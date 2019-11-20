from __future__ import print_function, division
import asyncio
import functools as ft

import ipywidgets as ipw
import serial
import serial.tools.list_ports


def get_port(vid, pid):
    try:
        port = next(p for p in serial.tools.list_ports.comports()
                    if p.vid == vid and p.pid == pid)
    except StopIteration:
        raise IOError('No matching port found.')
    device = serial.Serial(port.device)
    device.close()
    return port


def debug_widget(aremote):
    def reset_esp32():
        future = asyncio.run_coroutine_threadsafe(aremote.reset(),
                                                  aremote.device.loop)
    
        def on_done(f):
            print('Reset successful (%d bytes free)' % f.result())
        future.add_done_callback(on_done)
    
    debug_buttons = []
    
    button_reset = ipw.Button(description='Reset ESP32')
    button_reset.on_click(lambda *args: reset_esp32())
    debug_buttons.append(button_reset)
    
    hbox_debug = ipw.HBox(debug_buttons)
    return hbox_debug

# -----------------------------------------------------------------------------
# Single pump UI (i.e., one button per pump); can still run more than one at a time
def do_pump(aremote, addr, index, pulses_widget, period_widget, *args, **kwargs):
    loop = asyncio.get_event_loop()
    loop.create_task(asyncio.wait_for(aremote
                                      .create_task('motor_ctrl.pump', addr,
                                                   index, pulses_widget.value,
                                                   on_ms=150,
                                                   off_ms=int(period_widget
                                                              .value * 1e3) -
                                                   150),
                                      timeout=2))

# # Pump control
def pump_widget(aremote, pumps):
    loop = asyncio.get_event_loop()

    def set_direction(addr, index, on, *args, **kwargs):
        return asyncio.wait_for(aremote.call('motor_ctrl.set_direction', addr, index, on), timeout=2)

    buttons = []
    for name_i, pump_i in pumps.items():
        button_i = ipw.Button(description='Pump %s' % name_i)
        pulses_i = ipw.IntSlider(min=0, max=125, value=25, description='Pulses')
        period_i = ipw.FloatSlider(min=0., max=125., value=1.,
                                   description='Period (s)')
        button_i.on_click(ft.partial(do_pump, aremote, pump_i['addr'],
                                     pump_i['index'], pulses_i, period_i))
        buttons.append(ipw.HBox([button_i, pulses_i, period_i]))

    single_pump_ui = ipw.VBox(buttons)
    return single_pump_ui


def multi_pump_widget(aremote, pumps):
    # Multiple pump UI (i.e., one button to start multiple pumps simultaneously)
    pulses = ipw.IntSlider(min=0, max=125, value=25, description='Pulses')
    period = ipw.FloatSlider(min=0., max=125., value=1.,
                             description='Period (s)')
    button_pump = ipw.Button(description='Pump', tooltip='''\
    1) Use checkboxes to select one or more pumps.
    2) Select number of pulses.
    3) Click here to execute pulses.'''.strip())
    checkboxes = ipw.VBox([ipw.Checkbox(description=name_i, index=True)
                           for name_i in pumps])
    sliders = ipw.VBox([pulses, period])

    def on_multi_pump(pulses, period, *args, **kwargs):
        for c in checkboxes.children:
            if c.value:
                pump = pumps[c.description]
                do_pump(aremote, pump['addr'], pump['index'], pulses, period)

    button_pump.on_click(ft.partial(on_multi_pump, pulses, period))

    multi_pump_ui = ipw.HBox([checkboxes, sliders, button_pump])
    return multi_pump_ui


def control_widget(aremote, pumps, valves):
    single_pump_ui = pump_widget(aremote, pumps)
    multi_pump_ui = multi_pump_widget(aremote, pumps)
    hbox_debug = debug_widget(aremote)
    
    accordion = ipw.Accordion(children=[single_pump_ui, multi_pump_ui, hbox_debug])

    accordion.set_title(0, 'Single pump')
    accordion.set_title(1, 'Multiple pumps')
    accordion.set_title(2, 'Debug')

    label = ipw.Label()

    pump_ui = ipw.VBox([accordion, label])

    def valve_widget(addr, index, name, options=None):
        if options is None:
            options=['A', 'B']
        valve = ipw.RadioButtons(options=options,
                                 description='Valve %s' % name)

        def on_toggle(addr, index, message, *args, **kwargs):
            value = (message['new'] == 1)

            async def switch_valve():
                await aremote.call('motor_ctrl.set_direction', addr, index, value)
                await aremote.call('gc.collect')

            loop = asyncio.get_event_loop()
            loop.create_task(asyncio.wait_for(switch_valve(), timeout=2))

        valve.observe(ft.partial(on_toggle, addr, index), names='index')
        return valve

    valves_ui = ipw.VBox([valve_widget(valve['addr'], valve['index'], name)
                          for name, valve in valves.items()])
    return ipw.HBox([pump_ui, valves_ui])
