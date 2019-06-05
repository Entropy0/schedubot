#!/usr/bin/env python3.6
"""A helper class for Schedubot to enumerate used conversation states.
"""

from enum import IntEnum

class States(IntEnum):

    """A helper class for Schedubot to enumerate used conversation states.
    
    Attributes:
        CHOOSING_POLL_ADD (int): User is chosing which poll to add to a chat.
        CHOOSING_POLL_CLOSE (int): User is chosing which poll to close.
        CHOOSING_POLL_EDIT_DESCRIPTION (int): User is chosing which poll's description to edit.
        CHOOSING_POLL_EDIT_NAME (int): User is chosing which poll's name to edit.
        CHOOSING_POLL_PRINT (int): User is chosing which poll to print.
        DEFAULT (int): Default state.
        TYPING_DESCRIPTION (int): User is typing description for new poll.
        TYPING_LENGTH (int): User is typing length for new poll.
        TYPING_NAME (int): User is typing name for new poll.
        TYPING_POLL_EDIT_DESCRIPTION (int): User is typing new description for poll.
        TYPING_POLL_EDIT_NAME (int): User is typing new name for poll.
        TYPING_VOTE (int): User is casting their vote.
    """
    
    DEFAULT = -1
    TYPING_NAME = 0
    TYPING_LENGTH = 1
    TYPING_DESCRIPTION = 2
    CHOOSING_POLL_ADD = 3
    CHOOSING_POLL_CLOSE = 4
    CHOOSING_POLL_PRINT = 5
    CHOOSING_POLL_EDIT_NAME = 6
    TYPING_POLL_EDIT_NAME = 7
    CHOOSING_POLL_EDIT_DESCRIPTION = 8
    TYPING_POLL_EDIT_DESCRIPTION = 9
    TYPING_VOTE = 10
