#!/opt/local/bin/python3
import sys
import subprocess

fcst_date = "20210613000000"  # UTC

# 水平分布
stations = ["Japan", "Tokyo"]
progs = [
    "python/readgrib_gsm_mslp_reg.py", "python/readgrib_gsm_ccover_reg.py", 
    "python/readgrib_gsm_stemp_reg.py", "python/readgrib_gsm_rain_sum_reg.py",
    "python/readgrib_msm_mslp_reg.py", "python/readgrib_msm_ccover_reg.py", 
    "python/readgrib_msm_stemp_reg.py", "python/readgrib_msm_rain_sum_reg.py",
    "python/readgrib_msm_temp_reg.py", "python/readgrib_msm_ept_reg.py"
]
#
# 時系列図
stations_tvar = ["Tokyo"]
progs_tvar = [
    "python/readgrib_msm_tvar_reg.py", "python/readgrib_gsm_tvar_reg.py"
]
times_tvar = [36, 72]

if __name__ == '__main__':
    for sta in stations:
        for p in progs:
            res = subprocess.run([p, "--fcst_date", fcst_date, "--sta", sta],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            print(res.stdout.decode("utf-8"))
            print(res.stderr.decode("utf-8"))

    for sta in stations_tvar:
        for p, t in zip(progs_tvar, times_tvar):
            res = subprocess.run(
                [p, "--fcst_date", fcst_date, "--sta", sta, "--fcst_time", t],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            print(res.stdout.decode("utf-8"))
            print(res.stderr.decode("utf-8"))
