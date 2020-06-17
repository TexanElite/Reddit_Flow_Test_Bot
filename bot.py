import praw
import json
import time
import db
import atexit

CREDENTIALS_FILENAME = 'credentials.json'
RESPONSE_FILENAME = 'responses.json'

# Max time before post is ignored
MAX_TIME = 72

reddit = None
has_bot_started = False

class Response:

    ### RESPONSE CLASS ###
    # comment -> Comment body
    # code -> Identifying code of response (so the bot knows where it is in the flow chart)
    # redirect_codes -> (Optional) Dictionary of a response from the user to a code
    # end -> (default = False) States if it is at the end of a process
    # sticky -> (default = False) States if the user response should be posted
    def __init__(self, comment, code, redirect_codes=None, end=False, sticky=False):
        self.comment = comment
        self.code = code
        self.redirect_codes = redirect_codes
        self.sticky = sticky
        self.end = end


# Get credentials

CREDENTIALS_FILE = open(CREDENTIALS_FILENAME, 'r')
CREDENTIALS_JSON = json.loads(CREDENTIALS_FILE.read())

CLIENT_ID = CREDENTIALS_JSON['CLIENT_ID']
CLIENT_SECRET = CREDENTIALS_JSON['CLIENT_SECRET']
USER_AGENT = CREDENTIALS_JSON['USER_AGENT']
USERNAME = CREDENTIALS_JSON['USERNAME']
PASSWORD = CREDENTIALS_JSON['PASSWORD']

MODERATOR = CREDENTIALS_JSON['MODERATOR']
SUBREDDIT = CREDENTIALS_JSON['SUBREDDIT']

if not MODERATOR:
    MODERATOR = 'AutoModerator'

if not CLIENT_ID or not CLIENT_SECRET or not USER_AGENT or not USERNAME or not PASSWORD or not SUBREDDIT:
    print(f'Invalid credentials, please populate {CREDENTIALS_FILENAME} correctly')
    exit(0)

# Initialize responses

RESPONSE_FILE = open(RESPONSE_FILENAME, 'r')
RESPONSE_JSON = json.loads(RESPONSE_FILE.read())
RESPONSES = []

FIRST_RESPONSE_CODE = '1'
OLD_RESPONSE_MESSAGE = 'Sorry, your time has expired to approve your post'
INVALID_RESPONSE = 'Error, invalid response.'
APPROVAL_MESSAGE = 'Submission has been approved!'
SHUTDOWN_APPROVAL_MESSAGE = f'{USERNAME} is closing, so your post will be approved regardless of the interview status. Cheers!'
UNEXPECTED_SHUTDOWN_MESSAGE = f'{USERNAME} is OFFLINE', f'{USERNAME} is OFFLINE due to an unexpected error. Resume manually moderationg posts'

for key in RESPONSE_JSON:
    response = RESPONSE_JSON[key]
    if key == 'first_response_code':
        FIRST_RESPONSE_CODE = response
        continue
    comment = response['comment'].lower()
    code = response['code'].lower()
    redirect_codes = None
    end = False
    sticky = False

    if 'redirect_codes' in response:
        redirect_codes = dict()
        for key in response['redirect_codes']:
            redirect_codes[key] = response['redirect_codes'][key].lower()
    if 'end' in response:
        end = response['end']
    if 'sticky' in response:
        sticky = response['sticky']

    RESPONSES.append(Response(comment, code, redirect_codes, end, sticky))
    
# Keeps track of the current posts
post_watchlist = set()

def hour_difference(x, y):
    diff = abs(x - y)
    diff /= (60 * 60)
    return diff

def check_post_deleted(submission):
    if submission.selftext == '[deleted]':
        return True
    return False

def mod_in_comments(submission, mod):
    if submission == None or submission.comments == None:
        return False
    for comment in submission.comments:
        if comment.author.name == mod:
            return True
    return False

def get_response(code):
    for resp in RESPONSES:
        if resp.code == code:
            return resp
    return None

def parse_message(code, body):
    response = get_response(code)
    for redirect in response.redirect_codes:
        if redirect.lower() in body.lower():
            return response.redirect_codes[redirect]
    return None

def process_message(reddit, message):
    entry = db.get_entry(message.subject[4:].lower())
    if entry == None:
        return
    submission = reddit.submission(entry.id)
    if check_post_deleted(submission):
        remove_entry(entry.id)
        return
    code = entry.code
    body = message.body
    next_code = parse_message(code, body)
    if next_code == None:
        status = message.reply(f'{INVALID_RESPONSE}\n\n{get_response(code).comment}')
        if status == None:
            db.remove_entry(entry.id)
    else:
        response = get_response(next_code)
        assert(response != None)
        status = message.reply(response.comment)
        if status == None:
            db.remove_entry(entry.id)
            return
        if get_response(code).sticky:
            submission.reply(f'OP\'s response to the question "{get_response(code).comment}":  \n>{body}').mod.distinguish()
        if response.end:
            submission.mod.approve()
            submission.reply(f'{APPROVAL_MESSAGE}').mod.distinguish()
            db.remove_entry(entry.id)
        else:
            db.update_code(entry.id, next_code)
        
def process_submission(reddit, submission):
    print('Processing new submission: ' + submission.title)
    already_commented = False
    author = submission.author

    if hour_difference(submission.created_utc, time.time()) >= MAX_TIME:
        print('Old post, ignoring')
        return
    
    if submission.removed:
        print('Violates rules, ignoring')
        return

    for comment in submission.comments:
        if USERNAME == comment.author:
            already_commented = True

    if not already_commented:
        first_response = get_response(FIRST_RESPONSE_CODE)
        reddit.redditor(author.name).message(submission.url, first_response.comment)
        db.add_entry(submission.id.lower(), submission.url.lower(), author.name.lower(), FIRST_RESPONSE_CODE)
        print('Messaged author of new post')
        submission.mod.remove()

    print('Processed Successfully')

def approve_all(message=None):
    global reddit
    posts = db.get_all()
    if posts != None:
        for entry in posts:
            submission = reddit.submission(entry.id)
            print(submission.title)
            if not check_post_deleted(submission):
                submission.mod.approve()
                if message != None:
                    submission.author.message(entry.url, message)
            db.remove_entry(entry.id)


def close_bot():
    if not has_bot_started:
        return
    print('Approving posts on the waitlist, please wait.')
    approve_all(message=f'{USERNAME} is closing, so your post will be approved regardless of the interview status. Cheers!')
    print('Finished processing, closing out')

def main():
    global reddit
    global has_bot_started
    print(f'{CLIENT_ID}')
    try:
        reddit = praw.Reddit(client_id=CLIENT_ID,
                             client_secret=CLIENT_SECRET,
                             user_agent=USER_AGENT,
                             username=USERNAME,
                             password=PASSWORD)
        print(f"Authenticated as {reddit.user.me()}")
    except Exception:
        print('Invalid credentials, please enter correct credentials into {CREDENTIALS_FILENAME}')
        return

    try:

        subreddit = reddit.subreddit(SUBREDDIT)
        stream = subreddit.stream.submissions(pause_after=0)
        early_posts = set()

        db.initialize_database()
        approve_all()
        print('Approved remaining posts, waiting 5 seconds before startup:')
        time.sleep(5)

        # Ingore all older posts
        for submission in stream:
            if submission == None:
                break
        has_bot_started = True
        while True:

            ignored_posts = set()

            for submission in early_posts:
                if submission == None:
                    break
                updated_submission = reddit.submission(submission)
                if check_post_deleted(updated_submission):
                    ignored_posts.add(submission)
                    continue

                # Check if automoderator has commented
                automoderator = mod_in_comments(updated_submission, MODERATOR)
                if automoderator:
                    process_submission(reddit, updated_submission)
                    ignored_posts.add(submission)
            
            # Clear out ignored_posts
            for submission in ignored_posts:
                early_posts.remove(submission)

            # Check new submissions
            for submission in stream:
                if submission == None:
                    break
                if check_post_deleted(submission):
                    continue

                # Check if automoderator has commented
                automoderator = mod_in_comments(submission, MODERATOR)
                if not automoderator:
                    early_posts.add(submission.id)
                else:
                    process_submission(reddit, submission)
            
            # Check inbox
            for message in reddit.inbox.unread(limit=None):
                if isinstance(message, praw.models.Message):
                    print(f'Processing new message: {message.subject[4:]}')
                    # Mark as read so it won't do it again later
                    process_message(reddit, message)
                    message.mark_read()

            # Remove all old posts from database
            posts = db.get_all()
            if posts != None:
                for entry in posts:
                    submission = reddit.submission(entry.id)
                    if check_post_deleted(submission):
                        db.remove_entry(entry.id)
                    elif hour_difference(submission.created_utc, time.time()) >= MAX_TIME:
                        db.remove_entry(entry.id)
                        reddit.redditor(entry.author).message(OLD_RESPONSE_MESSAGE)
    except Exception:
        print('An error has occurred, approving all and restarting...')
        try:
            approve_all()
        except Exception:
            print('Approving failed, closing bot and sending modmail describing situation')
            reddit.subreddit(SUBREDDIT).message(UNEXPECTED_SHUTDOWN_MESSAGE)
            return
        time.sleep(60)
        main()

if __name__ == '__main__':
    atexit.register(close_bot)
    main()
