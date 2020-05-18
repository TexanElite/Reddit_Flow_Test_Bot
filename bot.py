import praw

CLIENT_ID = ''
CLIENT_SECRET = ''
USER_AGENT = ''
USERNAME = ''
PASSWORD = ''

SUBREDDIT = 'tobortobor'

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



RESPONSES = [Response('Have you attempted', 'a', redirect_codes={'yes': 'b', 'no': 'c'}),
             Response('b node', 'b', end=True),
             Response('c node', 'c', end=True)]

FIRST_RESPONSE_CODE = 'a'

def get_response(code):
    for resp in RESPONSES:
        if resp.code == code:
            return resp
    return None

def process(comment):
    parent = comment.parent()
    cur_response = None
    for resp in RESPONSES:
        if resp.code in parent.body:
            cur_response = resp
    if cur_response == None:
        print('Error while processing comment: Parent comment did not contain code')
        return

    if cur_response.end:
        print('Processed comment successfully: End of process')
        return

    next_code = None
    for redirect in cur_response.redirect_codes.keys():
        if redirect.lower() in comment.body.lower():
            next_code = cur_response.redirect_codes[redirect]
    if next_code == None:
        print('Processed comment successfully: User provided invalid response')
        comment.reply('Invalid response, please try responding with the valid responses.\n\n' + cur_response.comment + '\n\n' + 'Code: ' + cur_response.code)
    else:
        print('Processed comment successfully: User provided valid response')
        next_response = None
        next_response = get_response(next_code)
        comment.reply(next_response.comment + '\n\n' + 'Code: ' + next_response.code)


def main():

    reddit = praw.Reddit(client_id=CLIENT_ID,
                         client_secret=CLIENT_SECRET,
                         user_agent=USER_AGENT,
                         username=USERNAME,
                         password=PASSWORD)

    print(f"Authenticated as {reddit.user.me()}")

    subreddit = reddit.subreddit(SUBREDDIT)
    stream = subreddit.stream.submissions(pause_after=0)
    while True:
        for submission in stream:
            if submission == None:
                break
            print('Processing new submission: ' + submission.title)
            already_commented = False
            for comment in submission.comments:
                if reddit.user.me() == comment.author and FIRST_RESPONSE_CODE in comment.body:
                    already_commented = True
            if not already_commented:
                first_response = get_response(FIRST_RESPONSE_CODE)
                submission.reply(first_response.comment + '\n\n' + 'Code: ' + first_response.code)
                print('Added new top-level comment')
            print('Processed Successfully')
        # Check inbox
        for comment in reddit.inbox.unread(limit=None):
            if isinstance(comment, praw.models.Comment):
                print('Processing new comment:')
                if comment.subreddit.display_name.lower() != SUBREDDIT.lower():
                    print('Skipped comment: Incorrect subreddit')
                # Process comment
                process(comment)
                # Mark as read so it won't do it again later
                comment.mark_read()

if __name__ == '__main__':
    main()
