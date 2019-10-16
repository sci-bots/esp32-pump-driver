'''
.. versionadded:: X.X.X
'''
import asyncio
import functools as ft
import json
import os
import pathlib

from PySide2 import QtWidgets

from file_manager import (host_tree, RemoteFileTree, load_project_structure_,
                          list_to_tree)


class RemoteBase:
    def __init__(self, device):
        self.device = device

    def _base_call(self, base_message, command, *args, **kwargs):
        raise NotImplementedError

    def call(self, command, *args, **kwargs):
        return self._base_call({}, command, *args, **kwargs)

    def await_(self, command, *args, **kwargs):
        return self._base_call({'async': True}, command, *args, **kwargs)

    def create_task(self, command, *args, **kwargs):
        return self._base_call({'async': 'task'}, command, *args, **kwargs)


class Remote(RemoteBase):
    def _base_call(self, base_message, command, *args, **kwargs):
        message = base_message.copy()
        message.update({'command': command, 'args': args,
                        'kwargs': kwargs})
        self.device.write(json.dumps(message).encode('utf8') + b'\r\n')
        response = json.loads(self.device.readline())
        if 'error' in response:
            raise RuntimeError('Error: `%s`' % response['error'])
        return response['result']


class AsyncRemote(RemoteBase):
    def __init__(self, *args, **kwargs):
        self.lock = asyncio.Lock()
        super().__init__(*args, **kwargs)

    async def _base_call(self, base_message, command, *args, **kwargs):
        message = base_message.copy()
        message.update({'command': command, 'args': args,
                        'kwargs': kwargs})
        with await self.lock:
            await self.device.write(json.dumps(message).encode('utf8') +
                                    b'\r\n')
            response = json.loads(await self.device.readline())
        if 'error' in response:
            raise RuntimeError('Error: `%s`' % response['error'])
        return response['result']

    async def flush(self):
        while True:
            data = await self.device.read(1024)
            if not data:
                break
            await asyncio.sleep(.25)

    async def reset(self, delay=8.):
        '''
        Example usage:

            future = asyncio.run_coroutine_threadsafe(reset(7.5), adevice.loop)
            future.add_done_callback(lambda f: print(f.result()))
        '''
        try:
            await self.call('machine.reset')
        except Exception:
            pass

        # Wait for device to reboot.
        print('Wait for device to reboot.')
        await asyncio.sleep(delay)

        # Flush serial data to reach clean state.
        print('Flush serial data to reach clean state.')
        await self.flush()
        return await self.call('gc.mem_free')

    async def copy_ltor(self, local_path, remote_path, chunk_size=2 * 1024):
        with open(local_path, 'r') as input_:
            created = False
            while True:
                contents = input_.read(2 * 1024)
                if not contents:
                    break
                if not created:
                    mode = 'w'
                    created = True
                else:
                    mode = 'a'
                await self.call('open("%s", "%s").write' % (remote_path, mode), contents)
                await self.call('gc.collect')
                print('open("%s", "%s").write %d bytes' % (remote_path, mode, len(contents)))

    async def copy_rtol(self, remote_path, local_path, chunk_size=2 * 1024):
        parent, name = os.path.split(os.path.realpath(local_path))
        data = ''
        while True:
            contents = await self.call('util.read_at', remote_path, len(data),
                                       n=chunk_size)
            await self.call('gc.collect')
            if not contents:
                break
            else:
                data += contents
        pathlib.Path(parent).mkdir(parents=True, exist_ok=True)
        print('write %d bytes to: %s' % (len(data), local_path))
        with open(local_path, 'w') as output:
            output.write(data)

    def file_manager(self, root_path='.'):
        tree = host_tree(root_path)

        remote_tree = RemoteFileTree()

        widget = QtWidgets.QWidget()
        combined = QtWidgets.QHBoxLayout()
        combined.addWidget(tree)
        combined.addWidget(remote_tree)
        widget.setLayout(combined)

        async def refresh_remote_tree():
            file_info = await self.call('util.walk_files', '/')
            model = remote_tree.model()
            model.removeRows(0, model.rowCount())
            main_dict = list_to_tree(sorted(file_info))
            load_project_structure_(main_dict, remote_tree)
            remote_tree.expandAll()


        def on_copy_request(loop, sender, label, links):
            relative_root = tree.model().filePath(tree.rootIndex())
            async def wrapped():
                remote_changed = False
                for link in links:
                    if link.startswith('remote:///'):
                        source = link[len('remote://'):]
                        print('copy `%s` to `%s`' % (source,
                                                    relative_root + source))
                        await self.copy_rtol(source, relative_root + source)
                    elif link.startswith('file:///'):
                        source = os.path.relpath(link[len('file:///'):],
                                                relative_root)
                        target = ('/' + source).replace('\\', '/')
                        print('copy `%s` to `%s`' % (source, target))
                        await self.copy_ltor(link[len('file:///'):], target)
                        remote_changed = True
                    else:
                        print('no match: `%s`' % link)
                if remote_changed:
                    await refresh_remote_tree()

            loop.call_soon_threadsafe(loop.create_task, wrapped())

        loop = self.device.loop
        tree.copy_request.connect(ft.partial(on_copy_request, loop, tree,
                                             'local'))
        remote_tree.copy_request.connect(ft.partial(on_copy_request, loop,
                                                    remote_tree, 'remote'))

        asyncio.run_coroutine_threadsafe(refresh_remote_tree(), loop)
        return widget
