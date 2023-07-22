import logging
import os
import threading
import uuid
from typing import Tuple, AnyStr

from flask import Flask, request
from flask_restful import Resource, Api
from flask_sqlalchemy import SQLAlchemy
from option import Result, Err, Ok
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Mapped, mapped_column

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///messages.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
api = Api(app)
db = SQLAlchemy(app)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = 'messages'
ALLOWED_EXTENSIONS = {'txt'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

file_lock = threading.Lock()

# Create multiple threads to edit the file concurrently
num_threads = 5
threads = []


# ----- Start of Business Layer ----
class FileHandler:
    """Holds all file manipulation logic"""

    def __init__(self, file_path):
        self.file_path = file_path

    def read_content(self):
        with open(self.file_path, 'r') as file:
            return file.read()

    def edit_content(self, edited_content):
        # Acquire a lock to prevent other threads from accessing the file simultaneously

        def edit_file(file_path):
            with file_lock:
                with open(file_path, 'r+') as file:
                    # Move the file pointer to the beginning and write the edited content
                    file.seek(0)
                    file.write(edited_content)
                    file.truncate()
                    file.close()

        for i in range(num_threads):
            thread = threading.Thread(target=edit_file, args=(self.file_path,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()


# ----- End of Business Layer ----

# ----- Start of DB models Layer ----

class User(db.Model):
    """User persona represents the message creator"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_path = db.Column(db.String(255), unique=True, nullable=False)
    assignee_id: Mapped[int] = mapped_column(db.ForeignKey("user.id"), nullable=True)
    # assignee: Mapped["User"] = db.relationship(back_populates="messages")


# ----- End of DB models Layer ----

# ----- Start of Selectors ----
def next_message(db) -> Result[Tuple[Message, AnyStr], Tuple[AnyStr, int]]:
    """
    Select next available message for editing
    """
    message = db.session.query(Message). \
        with_for_update(of=Message, nowait=True, skip_locked=True). \
        order_by(Message.id.asc()). \
        filter(Message.assignee_id.is_(None)). \
        first()
    if not message:
        return Err(('No messages available', 404))
    content = FileHandler(message.file_path).read_content()
    return Ok((message, content))


def create_message(db, message_content) -> Result[Message, Err]:
    """Creating of message"""
    file_uuid = uuid.uuid4().hex
    filename = f"{file_uuid}.txt"
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    with open(file_path, 'w') as f:
        f.write(message_content)

    message = Message(file_path=file_path)
    try:
        db.session.add(message)
        db.session.commit()
        return Ok(message)
    except DatabaseError as e:
        logger.debug(f"error while creating message {e.code}")
        return Err("Error while creating message")


def edit_message(db, message_id, content, assignee_id) -> Result[Message, None]:
    """
    Editing message and assigning the reviewer
    Notice select for update is not working with sqlite properly
    """
    message = db.session.query(Message).\
        with_for_update(of=Message, nowait=True, skip_locked=True). \
        filter(Message.id == message_id).first()
    __import__('ipdb').set_trace()
    #TODO: the next block should be atomic
    file_handler = FileHandler(message.file_path)
    file_handler.edit_content(content)
    message.assignee_id = assignee_id
    db.session.add(message)
    db.session.commit()
    return Ok(message)


def get_or_create_user_by_username(db, username) -> Result[User, None]:
    instance = db.session.query(User).filter_by(username=username).first()
    if not instance:
        instance = User(username=username)
        db.session.add(instance)
        db.session.commit()
    return Ok(instance)


# ----- ENd of Selectors ----


class MessageResource(Resource):
    def post(self):
        message_content = request.json.get('message_content')
        if not message_content:
            return {'error': 'No message content provided'}, 400
        result = create_message(db, message_content)
        if result.is_ok:
            message = result.unwrap()
            return {'id': message.id}, 201
        return result.unwrap_err(), 400

    def put(self, user_id, message_id):
        message_content = request.json.get('message_content')
        result = edit_message(db, message_id, message_content, user_id)
        if result.is_err:
            return "Error happened while editing", 400
        return message_content, 200


class NextMessageResource(Resource):
    def get(self):
        result = next_message(db)
        if result.is_ok:
            message, content = result.unwrap()
            return {'id': message.id, 'message': content}
        return result.unwrap_err()


class UserResource(Resource):
    def post(self):
        """Get or create"""
        username = request.json.get("username")
        result = get_or_create_user_by_username(db, username)
        if result.ok():
            user = result.unwrap()
            return {"id": user.id, "username": user.username}
        return result.unwrap_err(), 400


api.add_resource(
    MessageResource,
    '/messages',
    '/edit/<int:user_id>/<int:message_id>'
)
api.add_resource(UserResource, '/user')
api.add_resource(NextMessageResource, '/next_message')

if __name__ == '__main__':
    with app.app_context():
        db.init_app(app)
        db.create_all()
        app.run(debug=True)
