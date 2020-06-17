# Reddit Post Interview Bot #
This bot was made with the intention of providing a interview with a user before allowing their post to be shown on the subreddit. This bot was heavily specialized for the r/HomeworkHelp subreddit. However, anyone is free to mess around with this code.

## How to Use ##
Create a credentials.json file (like shown in the repository) containing the information that follows:
* CLIENT\_ID -> The client id of your bot
* CLIENT\_SECRET -> The client secret of your bot
* USER\_AGENT -> Unique identifier for Reddit
* USERNAME -> The username of your bot
* PASSWORD -> The password to your bot account

If you have any questions about the following, visit <https://praw.readthedocs.io/en/latest/getting_started/quick_start.html>

These are also required in the credentials.json file:
* MODERATOR -> The name of your automoderator (The bot waits for automoderator to make a comment, defaults to AutoModerator)
* SUBREDDIT -> The name of your subreddit (If the bot does not have mod privledges on the subreddit, I have no idea what will happen. Just don't do it)
  
Then, make a responses.json file, with the following tips:

* A response object consists of 5 main variables:
    * Comment (The message that will be sent to the user)
    * Code (The unique identifier of this response)
    * Redirect Codes (A map that maps responses containing certain messages to other response codes, thus creating an interview flow)
    * Sticky (The user response to this question will be posted on the submission as a reply)
    * End (Signifies if this is response is the end of a interview; any user responses will now be ignored)

* Identify the first response that should be asked to the user with the following: `"first_response_code": "Code goes here"`
* An example responses.json is provided in the repository.
* If you want the bot to respond regardless of what the user responds with, you should put "" as the message. This is shown in the responses.json file

### Disclaimer ###
This is probably very buggy. I am a terrible developer, so don't blame me if your computer blows up. You did this to yourself. Also there's an MIT License
