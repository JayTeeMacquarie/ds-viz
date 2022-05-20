- Python 3.5 (or above) is required to run this program.
- Ensure that python3, pip3, and tkinter are installed with `sudo apt install python3 python3-tk python3-pip`
- Install required packages with `python3 -m pip install --user -r requirements.txt`
- Generate resource failure and log files with a particular configuration file
- Usage instructions (also provided with `python3 ./ds_viz.py -h`):
    - `python3 ./ds_viz.py config log` to visualise the contents of a simulation that used the
    config file `config` which had produced the log file named `log`.
    - `-f failures` to visualise failures from a resource failures file `failures`
    - `-c num` to specify the height of server cores to `num` pixels. Default is 8.
    - `-s num` to specify the initial scaling factor to `num`. Default is the maximum scaling factor possible.
    The scaling factor will determine the maximum number of cores to display per server, represented as an exponent
    of 2. E.g. a scale factor of 3 will display at most 8 cores per server.
    - `-w num` to specify the width of the visualisation as a multiple of window width. Default is 1. A width value
    of `1` will make the timeline fill the entire width of the window, a value of `2` will make the timeline twice
    as wide as the window.
- The following example will produce a visualisation of the server log saved in `g5k06-config100.xml.log`, using
the system information from `config100.xml` and the resource failure information from `g5k06-config100-fails.txt`.
Each core will be `10` pixels tall and the initial scaling factor is set to `2` (maximum of 4 cores per server).

        python3 ./ds_viz.py ./config100.xml -f ./g5k06-config100-fails.txt ./g5k06-config100.xml.log -c 10 -s 2

### Runtime instructions
- Click on the tabs above the information windows to switch between `Current Server` and `Current Job` for
the left window, and `Current Results` and `Final Results` for the right window.
- Press the `Show Job` button to toggle highlighting for the currently selected job.
- Selection:
    - Change the currently selected server by moving the `Server` slider. The information in `Current Server` will
    update accordingly, and the green highlight will move to the selected server.
    - Change the currently selected job by moving the `Job` slider. The information in `Current Job` will
    update accordingly. If `Show Job` is selected, then the currently selected job will be highlighted in yellow.
    - Change the time shown in the visualisation by moving the `Time` slider. The information in `Current Server`,
    `Current Job`, and `Current Results` will update accordingly.
    - These selections can also be made using the spinners (text boxes with arrows) next to the sliders. Type a
    particular value and press the enter key, or simply click on an arrow.
- Press the `-` or `+` button to decrease or increase the scaling factor, respectively.

### Troubleshooting
- If you receive a `X Error of failed request:  BadAlloc (insufficient resources for operation)` error and are
unable to increase your memory capacity, try reducing the core height by passing a lower number with the `-c`
option.# ds-viz
# ds-viz
