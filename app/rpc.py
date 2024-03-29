import gc
import json

import uasyncio as asyncio


async def rpc(areader, awriter, context=None):
    if context is not None:
        globals().update(context)
        print('Context:\n%s' % sorted(context.keys()))
    loop = asyncio.get_event_loop()
    stopped = False
    while not stopped:
        message_str = await areader.readline()
        try:
            message = json.loads(message_str)
            command = message.get('command')
            async_ = message.get('async')
            if command == '__stop__':
                stopped = True
                response = {'result': None}
            elif command == '__globals__':
                response = {'result': sorted(globals().keys())}
            elif command == '__locals__':
                response = {'result': sorted(locals().keys())}
            elif command:
                try:
                    func = eval(command)
                    result = func(*message.get('args', []),
                                  **message.get('kwargs', {}))
                    if async_ == 'task':
                        # create asyncio task and ignore result
                        loop.create_task(result)
                        result = None
                    elif async_:
                        # wait for async result
                        result = await result
                    response = {'result': result}
                except Exception as exception:
                    response = {'error': str(exception), 'command': command}
        except Exception as exception:
            response = {'error': str(exception)}
        await awriter.awrite(json.dumps(response) + '\r\n')
        gc.collect()
