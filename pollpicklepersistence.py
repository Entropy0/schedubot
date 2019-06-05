#!/usr/bin/env python3.6
"""Extend PicklePersistence to also keep track of polls.
"""

import pickle
from collections import defaultdict
from copy import deepcopy

from telegram.ext import PicklePersistence

class PollPicklePersistence(PicklePersistence):

    """An extended version of PicklePersistence to also keep track of polls.
    
    Attributes:
        chat_data (dict): Description
        conversations (dict): Description
        poll_data (dict): Description
        user_data (dict): Description
    """
    
    def __init__(self, filename, store_user_data=True, store_chat_data=True, singe_file=True, on_flush=False):
        """Summary
        
        Args:
            filename (str): The filename for storing the pickle files. When :attr:`single_file` is false this will be used as a prefix.
            store_user_data (bool, optional): Optional. Whether user_data should be saved by this persistence class.
            store_chat_data (bool, optional): Optional. Whether chat_data should be saved by this persistence class.
            singe_file (bool, optional): Optional. When ``False`` will store 3 sperate files of
                `filename_user_data`, `filename_chat_data` and `filename_conversations`. Default is ``True``.
            on_flush (bool, optional): When ``True`` will only save to file when :meth:`flush` is called and keep data in memory until that happens.
                When ``False`` will store data on any transaction *and* on call fo :meth:`flush`. Default is ``False``.
        """
        super().__init__(filename, store_user_data, store_chat_data, singe_file, on_flush)
        self.poll_data = None

    def load_singlefile(self):
        """Modified to also load poll_data.
        
        Raises:
            TypeError: Couldn't unpickle data.
        """
        try:
            filename = self.filename
            with open(self.filename, 'rb') as file_:
                all_ = pickle.load(file_)
                self.user_data = defaultdict(dict, all_['user_data'])
                self.chat_data = defaultdict(dict, all_['chat_data'])
                self.conversations = all_['conversations']
                self.poll_data = defaultdict(dict, all_['poll_data'])
        except IOError:
            self.conversations = {}
            self.user_data = defaultdict(dict)
            self.chat_data = defaultdict(dict)
            self.poll_data = defaultdict(dict)
        except pickle.UnpicklingError:
            raise TypeError(f"File {filename} does not contain valid pickle data")
        except Exception:
            raise TypeError(f"Something went wrong unpickling {filename}")


    def dump_singlefile(self):
        """Modified to also save poll_data.
        """
        with open(self.filename, 'wb') as file_:
            all_ = {'conversations': self.conversations, 'user_data': self.user_data, 'chat_data': self.chat_data, 'poll_data': self.poll_data}
            pickle.dump(all_, file_)


    def get_poll_data(self):
        """Returns the poll_data from the pickle file if it exsists or an empty defaultdict.
        
        Returns:
            TYPE: The restoreed polls.
        """
        if self.poll_data:
            pass
        elif not self.single_file:
            filename = f'{self.filename}_poll_data'
            data = self.load_file(filename)
            if not data:
                data = defaultdict(dict)
            else:
                data = defaultdict(dict, data)
            self.poll_data = data
        else:
            self.load_singlefile()
        return deepcopy(self.poll_data)


    def update_poll_data(self, poll_id, data):
        """Will update the poll_data (if changed) and depending on :attr:`on_flush` save the pickle file.
        
        Args:
            poll_id (int): The poll the data might have been changed for.
            data (dict): The :attr:`Poll` [poll_id].
        """
        if self.poll_data.get(poll_id) == data:
            return
        self.poll_data[poll_id] = data
        if not self.on_flush:
            if not self.single_file:
                filename = f'{self.filename}_poll_data'
                self.dump_file(filename, self.poll_data)
            else:
                self.dump_singlefile()


    def drop_poll_data(self, poll_id):
        """Will remove the poll from poll_data and depending on :attr:`on_flush` save the pickle file.
        
        Args:
            poll_id (int): The poll to drop.
        """
        if poll_id in self.poll_data:
            del self.poll_data[poll_id]
        if not self.on_flush:
            if not self.single_file:
                filename = f'{self.filename}_poll_data'
                self.dump_file(filename, self.poll_data)
            else:
                self.dump_singlefile()


    def flush(self):
        """Modified to handle poll_data.
        """
        if self.single_file:
            if self.user_data or self.chat_data or self.conversations or self.poll_data:
                self.dump_singlefile()
        else:
            if self.user_data:
                self.dump_file(f'{self.filename}_user_data', self.user_data)
            if self.chat_data:
                self.dump_file(f'{self.filename}_chat_data', self.chat_data)
            if self.conversations:
                self.dump_file(f'{self.filename}_conversations', self.conversations)
            if self.poll_data:
                self.dump_file(f'{self.filename}_poll_data', self.poll_data)
