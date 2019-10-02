# This file is executed on every boot (including wake-boot from deepsleep)
import sys

sys.path.append('/app')

try:
    from main import *

    main()
except ImportError:
    print('warning: no app found')
except Exception as e:
    print('warning: error starting app\n%s' % e)
