# Simulation throughput

I measured simulation throughput using Ripes `v2.2.6-106-g5b8a616` on Windows x86_64. The benchmark, [`tests/simulation_rate.s`](tests/simulation_rate.s), executes 64 passes over the same 128 KiB memory region, with 32,768 aligned word stores per pass. Each inner iteration contains one `sw`, two `addi` instructions, and a conditional branch. The program uses only RV32I instructions and has no LED renderer. The same benchmark was run three times on `RV32_ISS` and three times on `RV32_5S`, with a fresh Ripes CLI process for every trial. I used `--iret` to obtain the retired instruction count and `--exectime` to obtain the actual model execution time in milliseconds, rather than estimating elapsed time from simulated cycles and a clock rate. Throughput was calculated as:

$$
\text{instructions/s} = \frac{\text{retired instructions} \times 1000}{\text{execution time in milliseconds}}
$$

Every trial retired **8,388,868 instructions**. The table below shows the measured execution times and the median of the three throughput values for each model. The pipeline execution times varied substantially, so these results describe the observed throughput under the measurement conditions rather than a fixed simulation rate.

| Model | Trial 1 time | Trial 2 time | Trial 3 time | Median instructions/s |
| --- | ---: | ---: | ---: | ---: |
| `RV32_ISS` | 559 ms | 552 ms | 677 ms | 15,006,919 |
| `RV32_5S` | 60,084 ms | 103,705 ms | 31,495 ms | 139,619 |

Using these median rates to project the assignment's estimate of approximately $10^9$ instructions for a direct baseline translation gives about **66.6 seconds** on `RV32_ISS` and **119.4 minutes** on `RV32_5S`. These are estimates, not measured baseline execution times: the complete baseline was not run on the target, and its instruction mix and memory behavior may produce a different simulation rate. The projection illustrates why building the full BFS table is especially costly on a visual pipeline model. The measurements can be reproduced with [`measure_simulation_rate.py`](measure_simulation_rate.py); raw telemetry and commands are saved under `.build/simulation_rate/`.
