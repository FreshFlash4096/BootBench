# BootBench

```python
This test measures load on a Boot Device in a stacked environment.
Execute ./run.py <block-dev>.
FIO 3.20 or newer must be installed as a prerequisite.
Look at the final_result.txt file for output at the end of the run!

#from OCP Hyperscale NVMe Boot SSD Specification Version 1.0
```


This test is a pass if **sustained Read IOPS > 60K**
