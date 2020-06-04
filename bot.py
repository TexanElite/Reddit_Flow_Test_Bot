import praw
import json
import time

CLIENT_ID = ''
CLIENT_SECRET = ''
USER_AGENT = ''
USERNAME = ''
PASSWORD = ''

CLIENT_ID = '2K9u0FXO0gss5g'
CLIENT_SECRET = 'd5huwFvXOwxDNlwCtole3CSOakg'
USER_AGENT = 'flow_test_bot (u/txnelite)'
USERNAME = 'Flow_Test_txnelite'
PASSWORD = 'ECTURaGeNteWomPOSTaTeRlo'
SUBREDDIT = 'tobortobor'
MODERATOR = 'txnelite'

MAX_TIME = 1

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



#RESPONSES = [Response('Did you solve the problem?', '1', redirect_codes={'yes': '2', 'no': '3'}),
#             Response('Good job!', '2', end=True),
#             Response('Ok, describe what you have done to try and solve the problem', '3', redirect_codes={'':'4'}, sticky=True),
#             Response('Will post as a comment so everybody can see', '4', end=True)]

RESPONSE_FILENAME = 'responses.json'

RESPONSE_FILE = open(RESPONSE_FILENAME, 'r')
RESPONSE_JSON = json.loads(RESPONSE_FILE.read())
RESPONSES = []
for key in RESPONSE_JSON:
    response = RESPONSE_JSON[key]
    comment = response['comment']
    code = response['code']
    redirect_codes = None
    end = False
    sticky = False

    if 'redirect_codes' in response:
        redirect_codes = dict()
        for key in response['redirect_codes']:
            redirect_codes[key] = response['redirect_codes'][key]
    if 'end' in response:
        end = response['end']
        print(comment + ' has end ' + str(end))
    if 'sticky' in response:
        sticky = response['sticky']

    RESPONSES.append(Response(comment, code, redirect_codes, end, sticky))
    
FIRST_RESPONSE_CODE = '1'

# Keeps track of the current posts
post_watchlist = set()


def hour_difference(x, y):
    diff = abs(x - y)
    diff /= (60 * 60)
    return diff

def get_response(code):
    for resp in RESPONSES:
        if resp.code == code:
            return resp
    return None

def process_comment(comment):
    parent = comment.parent()
    submission = comment.submission
    cur_response = None
    for resp in RESPONSES:
        if resp.code in parent.body:
            cur_response = resp

    if cur_response == None:
        print('Error while processing comment: Parent comment did not contain code')
        return

    if cur_response.end:
        print('Processed comment successfully: Process finished')
        submission.mod.approve()
        return

    next_code = None
    for redirect in cur_response.redirect_codes.keys():
        if redirect.lower() in comment.body.lower():
            next_code = cur_response.redirect_codes[redirect]
    if next_code == None:
        print('Processed comment successfully: User provided invalid response')
        comment.reply(f'Invalid response, please try responding with the valid responses.\n\n{cur_response.comment}\n\nCode:{cur_response.code}').mod.distinguish('yes')
    else:
        print('Processed comment successfully: User provided valid response')
        next_response = get_response(next_code)
        if next_response.end:
            print('Processed comment successfully: End of process, posting submission to community')
            comment.submission.mod.approve()

        if cur_response.sticky:
            c = submission.reply('OP provided the following information:\n\n' + comment.body)
            if c != None:
                c.mod.distinguish('yes', sticky=True)

        comment.reply(next_response.comment + f'\n\nCode:   {next_response.code}').mod.distinguish('yes')

def process_submission(submission):
    print('Processing new submission: ' + submission.title)
    already_commented = False
    
    if hour_difference(submission.created_utc, time.time()) >= MAX_TIME:
        print('Old post, ignoring')
        return
    
    if submission.removed:
        print('Violates rules, ignoring')
        return

    for comment in submission.comments:
        if USERNAME == comment.author and FIRST_RESPONSE_CODE in comment.body:
            already_commented = True

    if not already_commented:
        first_response = get_response(FIRST_RESPONSE_CODE)
        submission.reply(first_response.comment + '\n\n' + 'Code: ' + first_response.code).mod.distinguish('yes', sticky=True)
        print('Added new top-level comment')
        submission.mod.remove()

    print('Processed Successfully')



def main():

    reddit = praw.Reddit(client_id=CLIENT_ID,
                         client_secret=CLIENT_SECRET,
                         user_agent=USER_AGENT,
                         username=USERNAME,
                         password=PASSWORD)

    print(f"Authenticated as {reddit.user.me()}")

    subreddit = reddit.subreddit(SUBREDDIT)
    stream = subreddit.stream.submissions(pause_after=0)
    early_posts = set()

    while True:

        ignored_posts = set()

        for submission in early_posts:
            if submission == None:
                break
            updated_submission = reddit.submission(submission)
            # Check if automoderator has commented
            automoderator = False
            for comment in updated_submission.comments:
                if comment.author.name == MODERATOR:
                    automoderator = True
            if not automoderator:
                if hour_difference(updated_submission.created_utc, time.time()) >= MAX_TIME:
                    ignored_posts.add(submission)
                continue

            process_submission(updated_submission)
            ignored_posts.add(submission)
        
        for submission in ignored_posts:
            early_posts.remove(submission)

        # Check new submissions
        for submission in stream:
            if submission == None:
                break
            # Check if automoderator has commented
            automoderator = False
            for comment in submission.comments:
                if comment.author.name == MODERATOR:
                    automoderator = True
            if not automoderator:
                early_posts.add(submission.id)
                break

            process_submission(submission)
        
        # Check inbox
        for comment in reddit.inbox.unread(limit=None):
            if isinstance(comment, praw.models.Comment):
                print('Processing new comment: ')
                if comment.subreddit.display_name.lower() != SUBREDDIT.lower():
                    # Ignore if it's the wrong subreddit
                    print('Skipped comment: Incorrect subreddit')
                elif comment.submission.author != comment.author:
                    # Ignore if it's not OP
                    print('Skipped comment: author is not OP')
                else:
                    # Process comment
                    process_comment(comment)
                # Mark as read so it won't do it again later
                comment.mark_read()

if __name__ == '__main__':
    main()
