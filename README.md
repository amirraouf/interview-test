# Interview Project
## Premise
You are making an application that will allow users to post messages that get saved to a file and then for other users
to read those messages, edit them and save them back to the file. The plan is to eventually support thousands of users
and millions of messages being edited and modified. Any message should only be edited by a single user at a time. The
contents of the messages are to be saved to files by design and will not change in the future.


## Assignment
- Plan on spending approximately **four hours** on this project.
- Determine what is feasible to complete in that time frame.
- Create a list of tasks that you would need to complete to get the application to a working state that cannot be completed in the time frame.
- Review the code and implement the most important features that you can in the time frame with a prioritization
  on implementing code that will grow with the application.
- The goal is not so much to get the code functioning as much as it is to demonstrate your thought process and
  how you would approach the problem with actual code written demonstrating how you structure your code.

## Other Considerations
- Given that the initial iteration is using local files, consider implementing a file handler that will grow with the application
and work with cloud services in the future.
- How should the application handle concurrency? What changes to the database model needs to happen?


## Usage:
For creating users
```bash
curl -X post http://127.0.0.1:5000/user --header 'Content-Type: application/json' -d '{"username":"amir"}'
```
For creating message
```bash
curl -X post http://127.0.0.1:5000/messages --header 'Content-Type: application/json' -d '{"message_content":"mariam3"}'
```
for getting next message
```bash
`curl -X get http://127.0.0.1:5000/next_message
```
for editing message
```bash
curl -X put http://127.0.0.1:5000/edit/1/5 --header 'Content-Type: application/json' -d '{"username":"amir3"}'
```