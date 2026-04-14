# Element classes for douyin-auto


class DouyinBase:
    """Base class for Douyin elements"""

    def __init__(self, hwnd=None):
        self._hwnd = hwnd

    @property
    def hwnd(self):
        """Window handle"""
        return self._hwnd


class VideoElement(DouyinBase):
    """
    Represents a video element.
    """

    def __init__(self, hwnd=None):
        super().__init__(hwnd)
        self._title = ''
        self._author = ''
        self._author_id = ''
        self._likes = 0
        self._comments = 0
        self._shares = 0
        self._duration = 0
        self._description = ''
        self._url = ''

    def __repr__(self):
        return f'<VideoElement: {self.title} by {self.author}>'

    @property
    def title(self):
        """Video title"""
        return self._title

    @title.setter
    def title(self, value):
        self._title = value

    @property
    def author(self):
        """Video author"""
        return self._author

    @author.setter
    def author(self, value):
        self._author = value

    @property
    def author_id(self):
        """Author ID"""
        return self._author_id

    @author_id.setter
    def author_id(self, value):
        self._author_id = value

    @property
    def likes(self):
        """Like count"""
        return self._likes

    @likes.setter
    def likes(self, value):
        self._likes = value

    @property
    def comments(self):
        """Comment count"""
        return self._comments

    @comments.setter
    def comments(self, value):
        self._comments = value

    @property
    def shares(self):
        """Share count"""
        return self._shares

    @shares.setter
    def shares(self, value):
        self._shares = value

    @property
    def duration(self):
        """Video duration in seconds"""
        return self._duration

    @duration.setter
    def duration(self, value):
        self._duration = value

    @property
    def description(self):
        """Video description"""
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    @property
    def url(self):
        """Video URL"""
        return self._url

    @url.setter
    def url(self, value):
        self._url = value


class CommentElement(DouyinBase):
    """
    Represents a comment element.
    """

    def __init__(self, hwnd=None):
        super().__init__(hwnd)
        self._id = ''
        self._user = ''
        self._user_id = ''
        self._content = ''
        self._likes = 0
        self._replies = 0
        self._time = ''
        self._is_reply = False
        self._parent_id = None

    def __repr__(self):
        return f'<CommentElement: {self.user}: {self.content[:30]}>'

    @property
    def id(self):
        """Comment ID"""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def user(self):
        """Comment user"""
        return self._user

    @user.setter
    def user(self, value):
        self._user = value

    @property
    def user_id(self):
        """User ID"""
        return self._user_id

    @user_id.setter
    def user_id(self, value):
        self._user_id = value

    @property
    def content(self):
        """Comment content"""
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    @property
    def likes(self):
        """Like count"""
        return self._likes

    @likes.setter
    def likes(self, value):
        self._likes = value

    @property
    def replies(self):
        """Reply count"""
        return self._replies

    @replies.setter
    def replies(self, value):
        self._replies = value

    @property
    def time(self):
        """Comment time"""
        return self._time

    @time.setter
    def time(self, value):
        self._time = value

    @property
    def is_reply(self):
        """Whether this is a reply"""
        return self._is_reply

    @is_reply.setter
    def is_reply(self, value):
        self._is_reply = value

    @property
    def parent_id(self):
        """Parent comment ID if this is a reply"""
        return self._parent_id

    @parent_id.setter
    def parent_id(self, value):
        self._parent_id = value


class UserElement(DouyinBase):
    """
    Represents a user element.
    """

    def __init__(self, hwnd=None):
        super().__init__(hwnd)
        self._id = ''
        self._nickname = ''
        self._signature = ''
        self._followers = 0
        self._following = 0
        self._likes = 0
        self._verified = False
        self._avatar_url = ''

    def __repr__(self):
        return f'<UserElement: {self.nickname}>'

    @property
    def id(self):
        """User ID"""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def nickname(self):
        """User nickname"""
        return self._nickname

    @nickname.setter
    def nickname(self, value):
        self._nickname = value

    @property
    def signature(self):
        """User signature/bio"""
        return self._signature

    @signature.setter
    def signature(self, value):
        self._signature = value

    @property
    def followers(self):
        """Follower count"""
        return self._followers

    @followers.setter
    def followers(self, value):
        self._followers = value

    @property
    def following(self):
        """Following count"""
        return self._following

    @following.setter
    def following(self, value):
        self._following = value

    @property
    def likes(self):
        """Total likes"""
        return self._likes

    @likes.setter
    def likes(self, value):
        self._likes = value

    @property
    def verified(self):
        """Whether user is verified"""
        return self._verified

    @verified.setter
    def verified(self, value):
        self._verified = value

    @property
    def avatar_url(self):
        """Avatar URL"""
        return self._avatar_url

    @avatar_url.setter
    def avatar_url(self, value):
        self._avatar_url = value


class MessageElement(DouyinBase):
    """
    Represents a private message element.
    """

    def __init__(self, hwnd=None):
        super().__init__(hwnd)
        self._id = ''
        self._sender = ''
        self._receiver = ''
        self._content = ''
        self._time = ''
        self._is_self = False
        self._read = False

    def __repr__(self):
        sender = 'Me' if self.is_self else self.sender
        return f'<MessageElement: {sender}: {self.content[:30]}>'

    @property
    def id(self):
        """Message ID"""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def sender(self):
        """Sender nickname"""
        return self._sender

    @sender.setter
    def sender(self, value):
        self._sender = value

    @property
    def receiver(self):
        """Receiver nickname"""
        return self._receiver

    @receiver.setter
    def receiver(self, value):
        self._receiver = value

    @property
    def content(self):
        """Message content"""
        return self._content

    @content.setter
    def content(self, value):
        self._content = value

    @property
    def time(self):
        """Message time"""
        return self._time

    @time.setter
    def time(self, value):
        self._time = value

    @property
    def is_self(self):
        """Whether this message is sent by self"""
        return self._is_self

    @is_self.setter
    def is_self(self, value):
        self._is_self = value

    @property
    def read(self):
        """Whether message is read"""
        return self._read

    @read.setter
    def read(self, value):
        self._read = value


class SessionElement(DouyinBase):
    """
    Represents a chat session element.
    """

    def __init__(self, hwnd=None):
        super().__init__(hwnd)
        self._id = ''
        self._name = ''
        self._last_message = ''
        self._last_time = ''
        self._unread = 0
        self._avatar = ''

    def __repr__(self):
        return f'<SessionElement: {self.name}>'

    @property
    def id(self):
        """Session ID"""
        return self._id

    @id.setter
    def id(self, value):
        self._id = value

    @property
    def name(self):
        """Session name (user nickname)"""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def last_message(self):
        """Last message content"""
        return self._last_message

    @last_message.setter
    def last_message(self, value):
        self._last_message = value

    @property
    def last_time(self):
        """Last message time"""
        return self._last_time

    @last_time.setter
    def last_time(self, value):
        self._last_time = value

    @property
    def unread(self):
        """Unread message count"""
        return self._unread

    @unread.setter
    def unread(self, value):
        self._unread = value

    @property
    def avatar(self):
        """Avatar URL or path"""
        return self._avatar

    @avatar.setter
    def avatar(self, value):
        self._avatar = value
