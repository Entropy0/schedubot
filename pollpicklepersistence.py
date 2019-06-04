#!/usr/bin/env python3.6

import pickle
from collections import defaultdict
from copy import deepcopy

from telegram.ext import PicklePersistence

class PollPicklePersistence(PicklePersistence):

    def __init__(self, filename, store_user_data=True, store_chat_data=True, singe_file=True, on_flush=False):
        super().__init__(filename, store_user_data, store_chat_data, singe_file, on_flush)
        self.poll_data = None

    def load_singlefile(self):
        try:
            filename = self.filename
            with open(self.filename, 'rb') as f:
                all = pickle.load(f)
                self.user_data = defaultdict(dict, all['user_data'])
                self.chat_data = defaultdict(dict, all['chat_data'])
                self.conversations = all['conversations']
                self.poll_data = defaultdict(dict, all['poll_data'])
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
        with open(self.filename, 'wb') as f:
            all = {'conversations': self.conversations, 'user_data': self.user_data, 'chat_data': self.chat_data, 'poll_data': self.poll_data}
            pickle.dump(all, f)


    def get_poll_data(self):
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
        if poll_id in self.poll_data:
            del self.poll_data[poll_id]
        if not self.on_flush:
            if not self.single_file:
                filename = f'{self.filename}_poll_data'
                self.dump_file(filename, self.poll_data)
            else:
                self.dump_singlefile()


    def flush(self):
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
