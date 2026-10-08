**What is the host-bytes-per-guest-byte ratio?**

I estimated the host-bytes-per-guest-byte ratio by comparing a small control program with programs that write to larger guest memory regions. `baseline_control.c` simply returns zero. `baseline_large.c` declares a global `volatile unsigned char` array and writes to every element; `volatile` prevents the compiler from eliminating these stores. The checked-in version uses a 4 MiB array, and the measurements cover region sizes of 1, 2, and 4 MiB. I recorded the Ripes process's memory usage in Windows Task Manager and subtracted the control measurement to estimate the additional host memory associated with each region.

| Guest region size (MiB) | Task Manager reading (displayed MB) | Increase over control |
| --- | ---: | ---: |
| 0 (control) | 156.5 | 0 |
| 1 | 204.0 | 47.5 |
| 2 | 252.3 | 95.8 |
| 4 | 348.9 | 192.4 |

Interpreting the Task Manager readings as binary MiB, the estimated ratio is:

$$
r = \frac{\text{host memory increase in bytes}}{\text{guest region size in bytes}}
$$

For the 4 MiB case:

$$
r = \frac{348.9 - 156.5}{4} = 48.1
$$

The 1, 2, and 4 MiB cases give approximately 47.5, 47.9, and 48.1 host bytes per guest byte, respectively. The approximately linear growth supports a rounded estimate of **48 host bytes per guest byte**. This empirical overhead is consistent with Ripes storing guest memory in a sparse, byte-addressed data structure rather than a contiguous host array. It is a property of this measurement environment, not a universal constant.

Applying the rounded ratio to the baseline's peak guest memory of 18,405,414 bytes gives:

$$
18{,}405{,}414 \times 48 = 883{,}459{,}872\text{ bytes} \approx 842.5\text{ MiB}
$$

This estimates the **additional** host memory associated with the baseline's guest memory. Adding the control measurement of 156.5 MiB gives an estimated total Ripes process footprint of approximately **999 MiB**. This is a projection; the full baseline was not executed in Ripes. Allocation behavior and sparse-memory container growth can affect the actual footprint. Because the large program uses a global array, the measurements describe the combined effect of loading and running each program, rather than proving that all additional memory was allocated by the stores during execution.

<!-- Before pasting into the final report, verify the binary interpretation of
the Task Manager readings and document the exact memory column, Ripes version,
processor model, compiler settings, when readings were taken, and whether Ripes
was restarted between measurements. These details have not yet been confirmed.
If the readings are decimal MB, the ratio must be converted accordingly. -->
