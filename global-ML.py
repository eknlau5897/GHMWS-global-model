import os
import time
import datetime
import concurrent.futures
import s3fs
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.ioff()

import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm
import metpy.calc as mpcalc

# -------------------------------------------------------------------------
# 1. AWS S3 & Output Path Setup
# -------------------------------------------------------------------------
fs = s3fs.S3FileSystem(anon=True)
BUCKET = "noaa-oar-mlwp-data"

AI_MODELS = {
    "Pangu": "PANG_v100_IFS",
    "GraphCast": "GRAP_v100_GFS",
}

base_output_dir = r"/Users/eknlau/VS_code/GHMWS-global-model/AIWP"
PROCESSED_LOG = os.path.join(base_output_dir, ".processed_runs.txt")

products = [
    "NWP/850hPa_wind_MSLP",
    "South China/850hPa_wind",
    "NWP/500hPa_GH_MSLP",
    "South China/10m_wind_MSLP"
]

for model_key in AI_MODELS.keys():
    for prod in products:
        os.makedirs(os.path.join(base_output_dir, model_key, prod), exist_ok=True)

def load_processed_runs():
    if os.path.exists(PROCESSED_LOG):
        with open(PROCESSED_LOG, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def mark_run_processed(run_id):
    with open(PROCESSED_LOG, "a") as f:
        f.write(f"{run_id}\n")

# -------------------------------------------------------------------------
# 2. Map Backgrounds & Visual Helpers
# -------------------------------------------------------------------------
def setup_ax_nw_pacific(ax):
    ax.set_extent([100, 170, 0, 60], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1, edgecolor='black')
    ax.add_feature(cfeature.STATES, linewidth=1, edgecolor='black')
    ax.add_feature(cfeature.BORDERS, linewidth=1, edgecolor='black')
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels, gl.left_labels = False, False
    return ax

def setup_ax_south_china(ax):
    ax.set_extent([105, 125, 15, 35], crs=ccrs.PlateCarree())
    ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1, edgecolor='black')
    ax.add_feature(cfeature.STATES, linewidth=1, edgecolor='black')
    ax.add_feature(cfeature.BORDERS, linewidth=1, edgecolor='black')
    gl = ax.gridlines(draw_labels=True)
    gl.top_labels, gl.left_labels = False, False
    return ax

gradient_colors = [
    "#FFFFFF", "#F0F0F0", "#E0E0E0", "#D0D0D0", "#80FFFF", "#70EFEF", "#60DFDF", "#50CFCF", 
    "#40BFBF", "#30AFAF", "#209F9F", "#108F8F", "#007F7F", "#009966", "#20A946", "#40B92C", 
    "#60C912", "#80D900", "#A0E920", "#C0F940", "#E0FF60", "#FFFF80", "#FFE960", "#FFD340", 
    "#FFBD20", "#FFA700", "#FF9100", "#FF7B00", "#FF6500", "#FF4F00", "#FF3900", "#990000", 
    "#A91010", "#B92020", "#C93030", "#D94040", "#9900CC", "#A910D2", "#B920D8", "#C930DE", 
    "#D940E4", "#E950EA", "#F960F0", "#FF70F6", "#FF80FC", "#FF90FC", "#FFA0F8", "#FFB0F4", 
    "#FFC0F0", "#FFD0EC", "#FFE0E8", "#FFF0E4", "#FFFFE0", "#FFE0E0", "#FFD0D0", "#FFC0C0", 
    "#FFB0B0", "#FFA0A0", "#FF9090", "#FF8080", "#FF7070", "#FF6060", "#FF5050", "#FF4040", 
    "#FF3030", "#FF2020", "#FF1010", "#FF0000", "#E00000", "#D00000", "#C00000", "#B00000", "#A00000", "#900000", "#800000"
]
cmap_wind = LinearSegmentedColormap.from_list("wind_smooth", gradient_colors, N=256)
wind_levels = [0, 7, 16, 25, 34, 40, 46, 52, 58, 64, 80, 96, 110, 125, 140, 155]
norm_wind = BoundaryNorm(wind_levels, cmap_wind.N)
mslp_levels = np.arange(800, 1100, 2)

def build_title_string(model_name, init_dt, fxx):
    try:
        valid_time = init_dt + pd.Timedelta(hours=fxx)
        valid_UTC = valid_time.strftime('%H:%M UTC %d %b %Y')
        valid_CST = (valid_time + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = init_dt.strftime('%H:%M UTC %d %b %Y')
        init_CST = (init_dt + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
    except Exception:
        valid_UTC, valid_CST, init_UTC, init_CST = "N/A", "N/A", "N/A", "N/A"
    
    return (
        f"{model_name} AIWP: 0.25 degree resolution\n"
        f"Valid: {valid_UTC} or {valid_CST}\n"
        f"initialized at {init_UTC} or {init_CST}\n"
        f"forecast hour:{fxx}\n"
        f"Plotted by HKMETC"
    )

def get_var(ds, possible_names):
    for name in possible_names:
        if name in ds:
            return ds[name]
    raise KeyError(f"None of {possible_names} found in dataset keys: {list(ds.keys())}")

def find_latest_s3_file(s3_folder):
    """Searches backwards for the latest netcdf/hdf run matching: noaa-oar-mlwp-data/MODEL/YYYY/MMDD/..."""
    now = datetime.datetime.now(datetime.timezone.utc)
    
    for days_back in range(7):
        target_date = now - datetime.timedelta(days=days_back)
        yyyy = target_date.strftime("%Y")
        mmdd = target_date.strftime("%m%d")
        
        base_path = f"{BUCKET}/{s3_folder}/{yyyy}/{mmdd}"
        
        try:
            if fs.exists(base_path):
                all_found = fs.find(base_path)
                nc_files = [f for f in all_found if f.endswith('.nc') or f.endswith('.h5') or 'f240' in f]
                if nc_files:
                    return sorted(nc_files)[-1]
        except Exception:
            continue

    return None

# -------------------------------------------------------------------------
# 3. Parallel Worker Function for Plotting
# -------------------------------------------------------------------------
def process_forecast_step(fxx, ds_full, model_name, init_dt, model_dir):
    try:
        # Index dataset by timedelta step, integer index, or time dimension
        if 'step' in ds_full.dims or 'step' in ds_full.coords:
            if pd.api.types.is_timedelta64_dtype(ds_full.step.dtype):
                ds = ds_full.sel(step=np.timedelta64(fxx, 'h'))
            else:
                step_idx = int(fxx // 6)
                ds = ds_full.isel(step=step_idx)
        elif 'time' in ds_full.dims and len(ds_full.time) > 1:
            step_idx = int(fxx // 6)
            ds = ds_full.isel(time=step_idx)
        else:
            ds = ds_full

        if 'level' in ds.dims:
            ds_850 = ds.sel(level=850)
            ds_500 = ds.sel(level=500)
        elif 'isobaricInhPa' in ds.dims:
            ds_850 = ds.sel(isobaricInhPa=850)
            ds_500 = ds.sel(isobaricInhPa=500)
        else:
            ds_850, ds_500 = ds, ds

        u850 = get_var(ds_850, ["u850", "u", "UGRD", "u_component_of_wind"])
        v850 = get_var(ds_850, ["v850", "v", "VGRD", "v_component_of_wind"])
        msl  = get_var(ds, ["msl", "prmsl", "PRMSL", "mslp", "mean_sea_level_pressure"])
        gh500 = get_var(ds_500, ["gh500", "gh", "HGT", "z", "geopotential"])
        u10  = get_var(ds, ["u10", "10u", "UGRD_10m", "10m_u_component_of_wind"])
        v10  = get_var(ds, ["v10", "10v", "VGRD_10m", "10m_v_component_of_wind"])

        wspd850 = mpcalc.wind_speed(u850, v850)
        wspd10  = mpcalc.wind_speed(u10, v10)

        lat_slice = slice(90, 0)
        lon_slice = slice(90, 180)

        u850_sub = u850.sel(latitude=lat_slice, longitude=lon_slice)[::5, ::5]
        v850_sub = v850.sel(latitude=lat_slice, longitude=lon_slice)[::5, ::5]
        wspd850_sub = wspd850.sel(latitude=lat_slice, longitude=lon_slice)
        msl_sub = msl.sel(latitude=lat_slice, longitude=lon_slice)
        gh500_sub = gh500.sel(latitude=lat_slice, longitude=lon_slice)

        save_opts = {'dpi': 100, 'bbox_inches': 'tight', 'pil_kwargs': {'compress_level': 1}}

        # 1. 850hPa Wind + MSLP (NW Pacific)
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': ccrs.PlateCarree()})
        setup_ax_nw_pacific(ax)
        p = ax.contourf(wspd850_sub.longitude, wspd850_sub.latitude, wspd850_sub * 3.6 / 1.852,
                        transform=ccrs.PlateCarree(), cmap=cmap_wind, norm=norm_wind, levels=wind_levels, alpha=0.85)
        cs = ax.contour(msl_sub.longitude, msl_sub.latitude, msl_sub / 100,
                        levels=mslp_levels, colors='black', linewidths=0.85, transform=ccrs.PlateCarree())
        ax.clabel(cs, inline=True, fontsize=10, fmt='%d')
        ax.barbs(u850_sub.longitude, u850_sub.latitude, u850_sub * 3.6 / 1.852, v850_sub * 3.6 / 1.852,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.9)
        ax.set_title('850hPa wind + MSLP(hPa)', fontsize=12)
        cb = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb.set_label('knots', size='medium')
        cb.set_ticks(wind_levels)
        fig.suptitle(build_title_string(model_name, init_dt, fxx), color='red', fontsize=14)
        plt.savefig(os.path.join(model_dir, "NWP/850hPa_wind_MSLP", f"{fxx:03d}.png"), **save_opts)
        plt.close(fig)

        # 2. 850hPa Wind (South China)
        u850_sc = u850.sel(latitude=lat_slice, longitude=lon_slice)[::3, ::3]
        v850_sc = v850.sel(latitude=lat_slice, longitude=lon_slice)[::3, ::3]
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': ccrs.PlateCarree()})
        setup_ax_south_china(ax)
        p = ax.contourf(wspd850_sub.longitude, wspd850_sub.latitude, wspd850_sub * 3.6 / 1.852,
                        transform=ccrs.PlateCarree(), cmap=cmap_wind, norm=norm_wind, levels=wind_levels, alpha=0.85)
        ax.barbs(u850_sc.longitude, u850_sc.latitude, u850_sc * 3.6 / 1.852, v850_sc * 3.6 / 1.852,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.85)
        ax.set_title('850hPa wind', fontsize=12)
        cb = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb.set_label('knots', size='medium')
        cb.set_ticks(wind_levels)
        fig.suptitle(build_title_string(model_name, init_dt, fxx), color='red', fontsize=14)
        plt.savefig(os.path.join(model_dir, "South China/850hPa_wind", f"{fxx:03d}.png"), **save_opts)
        plt.close(fig)

        # 3. 500hPa GH + MSLP (NW Pacific)
        gh_val = gh500_sub.values
        if np.nanmax(gh_val) > 10000:
            gh_dagpm = gh500_sub / 98.0665
        elif np.nanmax(gh_val) > 1000:
            gh_dagpm = gh500_sub / 10.0
        else:
            gh_dagpm = gh500_sub

        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': ccrs.PlateCarree()})
        setup_ax_nw_pacific(ax)
        p = ax.contourf(gh_dagpm.longitude, gh_dagpm.latitude, gh_dagpm,
                        transform=ccrs.PlateCarree(), cmap="turbo", levels=np.arange(468, 606, 6), alpha=0.85)
        cs = ax.contour(msl_sub.longitude, msl_sub.latitude, msl_sub / 100,
                        levels=mslp_levels, colors='black', linewidths=0.85, transform=ccrs.PlateCarree())
        ax.clabel(cs, inline=True, fontsize=10, fmt='%d')
        ax.set_title('500hPa Geopotential Height (dagpm) + MSLP(hPa)', fontsize=12)
        cb = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb.set_label('Geopotential Height (dagpm)', size='medium')
        cb.set_ticks(np.arange(468, 606, 6))
        fig.suptitle(build_title_string(model_name, init_dt, fxx), color='red', fontsize=14)
        plt.savefig(os.path.join(model_dir, "NWP/500hPa_GH_MSLP", f"{fxx:03d}.png"), **save_opts)
        plt.close(fig)

        # 4. 10m Wind + MSLP (South China)
        u10_sc = u10.sel(latitude=lat_slice, longitude=lon_slice)[::3, ::3]
        v10_sc = v10.sel(latitude=lat_slice, longitude=lon_slice)[::3, ::3]
        wspd10_sub = wspd10.sel(latitude=lat_slice, longitude=lon_slice)

        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw={'projection': ccrs.PlateCarree()})
        setup_ax_south_china(ax)
        p = ax.contourf(wspd10_sub.longitude, wspd10_sub.latitude, wspd10_sub * 3.6 / 1.852,
                        transform=ccrs.PlateCarree(), cmap=cmap_wind, norm=norm_wind, levels=wind_levels, alpha=0.85)
        ax.barbs(u10_sc.longitude, u10_sc.latitude, u10_sc * 3.6 / 1.852, v10_sc * 3.6 / 1.852,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.85)
        cs = ax.contour(msl_sub.longitude, msl_sub.latitude, msl_sub / 100,
                        levels=mslp_levels, colors='black', transform=ccrs.PlateCarree())
        ax.clabel(cs, fontsize=10, inline=1, inline_spacing=1, fmt='%i', rightside_up=True)
        ax.set_title('10m wind + MSLP(hPa)', fontsize=12)
        cb = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb.set_label('Knots', size='medium')
        cb.set_ticks(wind_levels)
        fig.suptitle(build_title_string(model_name, init_dt, fxx), color='red', fontsize=14)
        plt.savefig(os.path.join(model_dir, "South China/10m_wind_MSLP", f"{fxx:03d}.png"), **save_opts)
        plt.close(fig)

        print(f"   [Done] FXX {fxx:03d}")
    except Exception as e:
        print(f"❌ Failed FXX {fxx:03d}: {e}")

# -------------------------------------------------------------------------
# 4. Continuous Loop Execution
# -------------------------------------------------------------------------
fxx_list = [0, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 132, 144, 156, 168, 180, 192, 204, 216, 228, 240]
SLEEP_INTERVAL_MINUTES = 240

while True:
    processed_files = load_processed_runs()
    now_utc = datetime.datetime.now(datetime.timezone.utc)

    print(f"\n==========================================")
    print(f" 🔄 Run started at {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"==========================================")

    for model_name, s3_folder in AI_MODELS.items():
        print(f"\n--- Checking Model: {model_name} ---")
        model_dir = os.path.join(base_output_dir, model_name)
        
        target_s3_key = find_latest_s3_file(s3_folder)
        
        if not target_s3_key:
            print(f"⚠️ No recent runs found for model {model_name}")
            continue

        if target_s3_key in processed_files:
            print(f"ℹ️ {target_s3_key} already processed. Skipping.")
            continue

        print(f"⚡ Target S3 File: s3://{target_s3_key}")

        try:
            with fs.open(target_s3_key, 'rb') as s3_file:
                ds_full = xr.open_dataset(s3_file, engine='h5netcdf')
                print("✅ NetCDF dataset opened successfully!")

                if 'time' in ds_full.coords:
                    time_val = ds_full.time.values
                    init_dt = pd.to_datetime(time_val[0] if getattr(time_val, 'ndim', 0) > 0 else time_val)
                else:
                    # Parse initialization datetime directly from filename string (e.g. 2026081700)
                    filename = os.path.basename(target_s3_key)
                    try:
                        date_str = filename.split('_')[3]
                        init_dt = pd.to_datetime(date_str, format='%Y%m%d%H')
                    except Exception:
                        init_dt = pd.Timestamp.now()

                max_workers = min(os.cpu_count() or 4, 6)
                print(f"⚡ Plotting forecast steps in parallel ({max_workers} workers)...")

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [
                        executor.submit(process_forecast_step, fxx, ds_full, model_name, init_dt, model_dir)
                        for fxx in fxx_list
                    ]
                    concurrent.futures.wait(futures)

            mark_run_processed(target_s3_key)

        except Exception as e:
            print(f"❌ Error processing {model_name}: {e}")

    print(f"\n💤 Sleeping for {SLEEP_INTERVAL_MINUTES // 60} hours before next check...")
    time.sleep(SLEEP_INTERVAL_MINUTES * 60)