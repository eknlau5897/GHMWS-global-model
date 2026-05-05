import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from ecmwf.opendata import Client
import earthkit.data
from datetime import datetime
from herbie import Herbie
import numpy as np
from metpy import calc as mpcalc
from matplotlib.colors import LinearSegmentedColormap, BoundaryNorm

if len(sys.argv) < 2:
    print("Usage: python plot_weather.py YYYYMMDDHH")
    sys.exit(1)

input_date = sys.argv[1]
dt = datetime.strptime(input_date, "%Y%m%d%H")
run_str = dt.strftime("%Y-%m-%d %H:%M")

save_path = r"/Users/eknlau/VS_code/GHMWS-global-model/ECMWF/NWP/850hPa wind+MSLP" # Adjust for Linux if needed
os.makedirs(save_path, exist_ok=True)

fxx_list = [0,6,12,18,24,30,36,42, 48,54,60,66,72,78,84,90, 96,102,108,114, 120,126,132,138,144,150,156,162, 168,174,180, 192,204, 216,228, 240]

# 2. Main Processing Loop
for fxx in fxx_list:
    try:
        print(f"Fetching {run_str} FXX {fxx}...")
        
        def plot_background(ax):
            ax.set_extent([100,170,0,60])
            ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1, edgecolor='black')
            ax.add_feature(cfeature.STATES, linewidth=1, edgecolor='black')
            ax.add_feature(cfeature.BORDERS, linewidth=1, edgecolor='black')
            gl = ax.gridlines(draw_labels=True)
            gl.xlabels_top = False
            gl.ylabels_left = False
            return ax
    	
        def plot_background_2(ax2):
            ax2.set_extent([105,125,15,35])
            ax2.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=1, edgecolor='black')
            ax2.add_feature(cfeature.STATES, linewidth=1, edgecolor='black')
            ax2.add_feature(cfeature.BORDERS, linewidth=1, edgecolor='black')
            gl = ax2.gridlines(draw_labels=True)
            gl.xlabels_top = False
            gl.ylabels_left = False
            return ax2
        
        print(f"Fetching {run_str} FXX {fxx}...")
        H = Herbie(run_str, model="ifs", product="oper", fxx=fxx)

        ds_2 = H.xarray(":u:850")
        ds_3 = H.xarray(":v:850")
        ds_4 = mpcalc.wind_speed(ds_2.u, ds_3.v)
        ds_mslp = H.xarray(":msl:")

        ds_2 = ds_2.sel(latitude=slice(90, 0,5), longitude=slice(90, 180,5))
        ds_3 = ds_3.sel(latitude=slice(90, 0,5), longitude=slice(90, 180,5))
        ds_4 = ds_4.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        ds_mslp = ds_mslp.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        mslp_hpa = ds_mslp.msl / 100

        fig, ax = plt.subplots(figsize=(14, 14), constrained_layout=True,
                               subplot_kw={'projection': ccrs.PlateCarree()})
        plot_background(ax)

        gradient_colors = [
            "#FFFFFF", "#F0F0F0", "#E0E0E0", "#D0D0D0",
            "#80FFFF", "#70EFEF", "#60DFDF", "#50CFCF", "#40BFBF", "#30AFAF",
            "#209F9F", "#108F8F", "#007F7F",
            "#009966", "#20A946", "#40B92C", "#60C912",
            "#80D900", "#A0E920", "#C0F940", "#E0FF60",
            "#FFFF80", "#FFE960", "#FFD340", "#FFBD20", "#FFA700",
            "#FF9100", "#FF7B00", "#FF6500", "#FF4F00", "#FF3900",
            "#990000", "#A91010", "#B92020", "#C93030", "#D94040",
            "#9900CC", "#A910D2", "#B920D8", "#C930DE", "#D940E4",
            "#E950EA", "#F960F0", "#FF70F6", "#FF80FC",
            "#FF90FC", "#FFA0F8", "#FFB0F4", "#FFC0F0", "#FFD0EC",
            "#FFE0E8", "#FFF0E4", "#FFFFE0",
            "#FFE0E0", "#FFD0D0", "#FFC0C0", "#FFB0B0", "#FFA0A0",
            "#FF9090", "#FF8080", "#FF7070", "#FF6060", "#FF5050",
            "#FF4040", "#FF3030", "#FF2020", "#FF1010", "#FF0000",
            "#E00000", "#D00000", "#C00000", "#B00000", "#A00000",
            "#900000", "#800000"
        ]
        cmap_custom = LinearSegmentedColormap.from_list("wind_smooth_original", gradient_colors, N=256)
        custom_levels = [0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155]
        norm_custom = BoundaryNorm(custom_levels, cmap_custom.N)

        p = ax.contourf(
        ds_4.longitude,
        ds_4.latitude,
        ds_4*3.6/1.852,
        transform=ccrs.PlateCarree(),
        cmap=cmap_custom,
        norm=norm_custom,
        levels=custom_levels,
        alpha=0.85
        )

        mslp_levels = np.arange(800, 1100, 2)
        cs = ax.contour(ds_mslp.longitude, ds_mslp.latitude, mslp_hpa,
                        levels=mslp_levels, colors='black', linewidths=0.85,
                        transform=ccrs.PlateCarree())
        ax.clabel(cs, inline=True, fontsize=10, fmt='%d')

        u_kts = ds_2.u * 3.6 / 1.852
        v_kts = ds_3.v * 3.6 / 1.852
        ax.barbs(ds_2.longitude, ds_2.latitude, u_kts, v_kts,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.9)

        ax.set_title(f'850hPa wind + MSLP(hPa)', fontsize=14)

        cb1 = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb1.set_label(f'knots', size='x-large')
        cb1.set_ticks([0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155])
        cb1.ax.tick_params(labelsize=12)

        valid_UTC = ds_2.valid_time.dt.strftime('%H:%M UTC %d %b %Y').item()
        valid_CST = (pd.to_datetime(ds_2.valid_time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = ds_2.time.dt.strftime('%H:%M UTC %d %b %Y').item()
        init_CST = (pd.to_datetime(ds_2.time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')

        fig.suptitle(
            f"ECMWF: 0.25 degree resolution\nValid: {valid_UTC} or {valid_CST}\ninitialized at {init_UTC} or {init_CST}\nforecast hour:{H.fxx}\nPlotted by GHMWS",
            color='red', fontsize=16
        )

        filename = f"{fxx}.png"
        save_full_path = os.path.join(save_path, filename)
        plt.savefig(save_full_path, dpi=150, bbox_inches='tight')
        plt.close(fig)  

        print("所有圖片已全部生成！")
        save_path_2 = r"/Users/eknlau/VS_code/GHMWS-global-model/ECMWF/South China/850hPa wind"
        os.makedirs(save_path_2, exist_ok=True)

        print(f"Fetching {run_str} FXX {fxx}...")
        H = Herbie(run_str, model="ifs", product="oper", fxx=fxx)

        ds_2 = H.xarray(":u:850")
        ds_3 = H.xarray(":v:850")
        ds_4 = mpcalc.wind_speed(ds_2.u, ds_3.v)

        ds_2 = ds_2.sel(latitude=slice(90, 0,3), longitude=slice(90, 180,3))
        ds_3 = ds_3.sel(latitude=slice(90, 0,3), longitude=slice(90, 180,3))
        ds_4 = ds_4.sel(latitude=slice(90, 0), longitude=slice(90, 180))

        fig, ax2 = plt.subplots(figsize=(14, 14), constrained_layout=True,
                                   subplot_kw={'projection': ccrs.PlateCarree()})
        plot_background_2(ax2)

        gradient_colors = [
            "#FFFFFF", "#F0F0F0", "#E0E0E0", "#D0D0D0",
            "#80FFFF", "#70EFEF", "#60DFDF", "#50CFCF", "#40BFBF", "#30AFAF",
            "#209F9F", "#108F8F", "#007F7F",
            "#009966", "#20A946", "#40B92C", "#60C912",
            "#80D900", "#A0E920", "#C0F940", "#E0FF60",
            "#FFFF80", "#FFE960", "#FFD340", "#FFBD20", "#FFA700",
            "#FF9100", "#FF7B00", "#FF6500", "#FF4F00", "#FF3900",
            "#990000", "#A91010", "#B92020", "#C93030", "#D94040",
            "#9900CC", "#A910D2", "#B920D8", "#C930DE", "#D940E4",
            "#E950EA", "#F960F0", "#FF70F6", "#FF80FC",
            "#FF90FC", "#FFA0F8", "#FFB0F4", "#FFC0F0", "#FFD0EC",
            "#FFE0E8", "#FFF0E4", "#FFFFE0",
            "#FFE0E0", "#FFD0D0", "#FFC0C0", "#FFB0B0", "#FFA0A0",
            "#FF9090", "#FF8080", "#FF7070", "#FF6060", "#FF5050",
            "#FF4040", "#FF3030", "#FF2020", "#FF1010", "#FF0000",
            "#E00000", "#D00000", "#C00000", "#B00000", "#A00000",
            "#900000", "#800000"
        ]
        cmap_custom = LinearSegmentedColormap.from_list("wind_smooth_original", gradient_colors, N=256)
        custom_levels = [0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155]
        norm_custom = BoundaryNorm(custom_levels, cmap_custom.N)

        p = ax2.contourf(
            ds_4.longitude,
            ds_4.latitude,
            ds_4*3.6/1.852,
            transform=ccrs.PlateCarree(),
            cmap=cmap_custom,
            norm=norm_custom,
            levels=custom_levels,
            alpha=0.85
        )

        u_kts = ds_2.u * 3.6 / 1.852
        v_kts = ds_3.v * 3.6 / 1.852
        ax2.barbs(ds_2.longitude, ds_2.latitude, u_kts, v_kts,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.85)

        ax2.set_title(f'850hPa wind', fontsize=14)

        cb1 = fig.colorbar(p, ax=ax2, orientation='horizontal')
        cb1.set_label(f'knots', size='x-large')
        cb1.set_ticks([0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155])
        cb1.ax.tick_params(labelsize=12)

        valid_UTC = ds_2.valid_time.dt.strftime('%H:%M UTC %d %b %Y').item()
        valid_CST = (pd.to_datetime(ds_2.valid_time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = ds_2.time.dt.strftime('%H:%M UTC %d %b %Y').item()
        init_CST = (pd.to_datetime(ds_2.time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')

        fig.suptitle(
            f"ECMWF: 0.25 degree resolution\nValid: {valid_UTC} or {valid_CST}\ninitialized at {init_UTC} or {init_CST}\nforecast hour:{H.fxx}\nPlotted by GHMWS",
            color='red', fontsize=16
        )

        filename = f"{fxx}.png"
        save_full_path = os.path.join(save_path_2, filename)
        plt.savefig(save_full_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print("所有圖片已全部生成！")
        save_path_3=r"/Users/eknlau/VS_code/GHMWS-global-model/ECMWF/NWP/500hPa GH+MSLP"
        os.makedirs(save_path, exist_ok=True)
        print(f"Fetching {run_str} FXX {fxx}...")
        H = Herbie(run_str, model="ifs", product="oper", fxx=fxx)

        ds_gh = H.xarray(":gh:500")
        ds_mslp = H.xarray(":msl:")

        ds_gh = ds_gh.sel(latitude=slice(90, 0,5), longitude=slice(90, 180,5))
        ds_mslp = ds_mslp.sel(latitude=slice(90, 0), longitude=slice(90, 180))
    
        gh_dagpm = ds_gh.gh / 10  
        mslp_hpa = ds_mslp.msl / 100

        fig, ax = plt.subplots(figsize=(14, 14), constrained_layout=True,
                               subplot_kw={'projection': ccrs.PlateCarree()})
        plot_background(ax)

        p = ax.contourf(
            gh_dagpm.longitude,
            gh_dagpm.latitude,
            gh_dagpm,
            transform=ccrs.PlateCarree(),
            cmap="turbo",
            levels=np.arange(468, 606, 6),
            alpha=0.85
        )

        mslp_levels = np.arange(800, 1100, 2)
        cs = ax.contour(ds_mslp.longitude, ds_mslp.latitude, mslp_hpa,
                        levels=mslp_levels, colors='black', linewidths=0.85,
                        transform=ccrs.PlateCarree())
        ax.clabel(cs, inline=True, fontsize=10, fmt='%d')

        ax.set_title(f'500hPa Geopotential Height (dagpm) + MSLP(hPa)', fontsize=14)

        cb1 = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb1.set_label(f'Geopotential Height (dagpm)', size='x-large')
        cb1.set_ticks(np.arange(468, 606, 6))
        cb1.ax.tick_params(labelsize=12)

        valid_UTC = ds_gh.valid_time.dt.strftime('%H:%M UTC %d %b %Y').item()
        valid_CST = (pd.to_datetime(ds_gh.valid_time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = ds_gh.time.dt.strftime('%H:%M UTC %d %b %Y').item()
        init_CST = (pd.to_datetime(ds_gh.time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')

        fig.suptitle(
            f"ECMWF: 0.25 degree resolution\nValid: {valid_UTC} or {valid_CST}\ninitialized at {init_UTC} or {init_CST}\nforecast hour:{H.fxx}\nPlotted by GHMWS",
            color='red', fontsize=16
        )

        filename = f"{fxx}.png"
        save_full_path = os.path.join(save_path_3, filename)
        plt.savefig(save_full_path, dpi=150, bbox_inches='tight')
        plt.close(fig)  

        print("所有圖片已全部生成！")
        save_path_4=r"/Users/eknlau/VS_code/GHMWS-global-model/ECMWF/South China/10m wind + MSLP"
        os.makedirs(save_path_4, exist_ok=True)
        print(f"Fetching {run_str} FXX {fxx}...")
        H = Herbie(run_str, model="ifs", product="oper", fxx=fxx)
        ds_2 = H.xarray(":10u:")
        ds_3 = H.xarray(":10v:")
        ds_4 = mpcalc.wind_speed(ds_2.u10, ds_3.v10)
        ds_11 = H.xarray("msl")
        ds_2 = ds_2.sel(latitude=slice(90, 0,3), longitude=slice(90, 180,3))
        ds_3 = ds_3.sel(latitude=slice(90, 0,3), longitude=slice(90, 180,3))
        ds_4 = ds_4.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        ds_11 = ds_11.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        fig, ax2 = plt.subplots(figsize=(12, 12), constrained_layout=True, subplot_kw={'projection': ccrs.PlateCarree()})
        plot_background_2(ax2)

        gradient_colors = [
            "#FFFFFF", "#F0F0F0", "#E0E0E0", "#D0D0D0",
            "#80FFFF", "#70EFEF", "#60DFDF", "#50CFCF", "#40BFBF", "#30AFAF",
            "#209F9F", "#108F8F", "#007F7F",
            "#009966", "#20A946", "#40B92C", "#60C912",
            "#80D900", "#A0E920", "#C0F940", "#E0FF60",
            "#FFFF80", "#FFE960", "#FFD340", "#FFBD20", "#FFA700",
            "#FF9100", "#FF7B00", "#FF6500", "#FF4F00", "#FF3900",
            "#990000", "#A91010", "#B92020", "#C93030", "#D94040",
            "#9900CC", "#A910D2", "#B920D8", "#C930DE", "#D940E4",
            "#E950EA", "#F960F0", "#FF70F6", "#FF80FC",
            "#FF90FC", "#FFA0F8", "#FFB0F4", "#FFC0F0", "#FFD0EC",
            "#FFE0E8", "#FFF0E4", "#FFFFE0",
            "#FFE0E0", "#FFD0D0", "#FFC0C0", "#FFB0B0", "#FFA0A0",
            "#FF9090", "#FF8080", "#FF7070", "#FF6060", "#FF5050",
            "#FF4040", "#FF3030", "#FF2020", "#FF1010", "#FF0000",
            "#E00000", "#D00000", "#C00000", "#B00000", "#A00000",
            "#900000", "#800000"
        ]
        cmap_custom = LinearSegmentedColormap.from_list("wind_smooth_original", gradient_colors, N=256)
        custom_levels = [0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155]
        norm_custom = BoundaryNorm(custom_levels, cmap_custom.N)

        p = ax2.contourf(
            ds_4.longitude,
            ds_4.latitude,
            ds_4*3.6/1.852,
            transform=ccrs.PlateCarree(),
            cmap=cmap_custom,
            norm=norm_custom,
            levels=custom_levels,
            alpha=0.85
        )

        u_kts = ds_2.u10 * 3.6 / 1.852
        v_kts = ds_3.v10 * 3.6 / 1.852
        ax2.barbs(ds_2.longitude, ds_2.latitude, u_kts, v_kts,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.85)

        msl_contour = ax2.contour(
            ds_11.longitude,
            ds_11.latitude,
            ds_11.msl/100,
            levels=np.arange(800, 1100, 2),
            colors='black',
            transform=ccrs.PlateCarree()
        )

        ax2.clabel(msl_contour, fontsize=10, inline=1, inline_spacing=1, fmt='%i', rightside_up=True)

        ax2.set_title(f'10m wind + MSLP(hPa)', fontsize=14)
        cb1 = fig.colorbar(p, ax=ax2, orientation='horizontal')
        cb1.set_label(f'Knots', size='x-large')
        cb1.set_ticks([0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155])
        cb1.ax.tick_params(labelsize=12)

        valid_UTC = ds_2.valid_time.dt.strftime('%H:%M UTC %d %b %Y').item()
        valid_CST = (pd.to_datetime(ds_2.valid_time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = ds_2.time.dt.strftime('%H:%M UTC %d %b %Y').item()
        init_CST = (pd.to_datetime(ds_2.time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')

        fig.suptitle(
            f"ECMWF: 0.25 degree resolution\nValid: {valid_UTC} or {valid_CST}\ninitialized at {init_UTC} or {init_CST}\nforecast hour:{fxx}\nPlotted by GHMWS",
            color='red', fontsize=16
        )

        save_full_path = os.path.join(save_path_4, f"{fxx}.png")
        plt.savefig(save_full_path, dpi=150, bbox_inches='tight')
        plt.close()

        print("所有圖片已全部生成！")
        save_path_5=r"/Users/eknlau/VS_code/GHMWS-global-model/GFS/NWP/500hPa GH MSLP"
        os.makedirs(save_path, exist_ok=True)
        print(f"Fetching {run_str} FXX {fxx}...")
        H = Herbie(run_str, model="gfs", product="pgrb2.0p25", fxx=fxx)

        ds_gh = H.xarray(":HGT:500")
        ds_mslp = H.xarray(":PRMSL:")

        ds_gh = ds_gh.sel(latitude=slice(90, 0,5), longitude=slice(90, 180,5))
        ds_mslp = ds_mslp.sel(latitude=slice(90, 0), longitude=slice(90, 180))
    
        gh_dagpm = ds_gh.gh  
        mslp_hpa = ds_mslp.prmsl / 100

        fig, ax = plt.subplots(figsize=(14, 14), constrained_layout=True,
                               subplot_kw={'projection': ccrs.PlateCarree()})
        plot_background(ax)

        p = ax.contourf(
            gh_dagpm.longitude,
            gh_dagpm.latitude,
            gh_dagpm,
            transform=ccrs.PlateCarree(),
            cmap="turbo",
            levels=np.arange(4680, 6060, 60),
            alpha=0.85
        )

        mslp_levels = np.arange(800, 1100, 2)
        cs = ax.contour(ds_mslp.longitude, ds_mslp.latitude, mslp_hpa,
                        levels=mslp_levels, colors='black', linewidths=0.85,
                        transform=ccrs.PlateCarree())
        ax.clabel(cs, inline=True, fontsize=10, fmt='%d')

        ax.set_title(f'500hPa Geopotential Height (dagpm) + MSLP(hPa)', fontsize=14)

        cb1 = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb1.set_label(f'Geopotential Height (dagpm)', size='x-large')
        cb1.set_ticks(np.arange(4680, 6060, 60))
        cb1.ax.tick_params(labelsize=12)

        valid_UTC = ds_gh.valid_time.dt.strftime('%H:%M UTC %d %b %Y').item()
        valid_CST = (pd.to_datetime(ds_gh.valid_time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = ds_gh.time.dt.strftime('%H:%M UTC %d %b %Y').item()
        init_CST = (pd.to_datetime(ds_gh.time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')

        fig.suptitle(
            f"GFS: 0.25 degree resolution\nValid: {valid_UTC} or {valid_CST}\ninitialized at {init_UTC} or {init_CST}\nforecast hour:{H.fxx}\nPlotted by GHMWS",
            color='red', fontsize=16
        )

        filename = f"{fxx}.png"
        save_full_path = os.path.join(save_path_5, filename)
        plt.savefig(save_full_path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print("所有圖片已全部生成！")
        save_path_6=r"/Users/eknlau/VS_code/GHMWS-global-model/GFS/NWP/850hPa wind MSLP"
        H = Herbie(run_str, model="gfs", product="pgrb2.0p25", fxx=fxx)

        ds_2 = H.xarray(":UGRD:850")
        ds_3 = H.xarray(":VGRD:850")
        ds_4 = mpcalc.wind_speed(ds_2.u, ds_3.v)
        ds_mslp = H.xarray("PRMSL")

        ds_2 = ds_2.sel(latitude=slice(90, 0,5), longitude=slice(90, 180,5))
        ds_3 = ds_3.sel(latitude=slice(90, 0,5), longitude=slice(90, 180,5))
        ds_4 = ds_4.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        ds_mslp = ds_mslp.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        mslp_hpa = ds_mslp.prmsl / 100

        fig, ax = plt.subplots(figsize=(14, 14), constrained_layout=True,
                               subplot_kw={'projection': ccrs.PlateCarree()})
        plot_background(ax)

        gradient_colors = [
            "#FFFFFF", "#F0F0F0", "#E0E0E0", "#D0D0D0",
            "#80FFFF", "#70EFEF", "#60DFDF", "#50CFCF", "#40BFBF", "#30AFAF",
            "#209F9F", "#108F8F", "#007F7F",
            "#009966", "#20A946", "#40B92C", "#60C912",
            "#80D900", "#A0E920", "#C0F940", "#E0FF60",
            "#FFFF80", "#FFE960", "#FFD340", "#FFBD20", "#FFA700",
            "#FF9100", "#FF7B00", "#FF6500", "#FF4F00", "#FF3900",
            "#990000", "#A91010", "#B92020", "#C93030", "#D94040",
            "#9900CC", "#A910D2", "#B920D8", "#C930DE", "#D940E4",
            "#E950EA", "#F960F0", "#FF70F6", "#FF80FC",
            "#FF90FC", "#FFA0F8", "#FFB0F4", "#FFC0F0", "#FFD0EC",
            "#FFE0E8", "#FFF0E4", "#FFFFE0",
            "#FFE0E0", "#FFD0D0", "#FFC0C0", "#FFB0B0", "#FFA0A0",
            "#FF9090", "#FF8080", "#FF7070", "#FF6060", "#FF5050",
            "#FF4040", "#FF3030", "#FF2020", "#FF1010", "#FF0000",
            "#E00000", "#D00000", "#C00000", "#B00000", "#A00000",
            "#900000", "#800000"
        ]
        cmap_custom = LinearSegmentedColormap.from_list("wind_smooth_original", gradient_colors, N=256)
        custom_levels = [0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155]
        norm_custom = BoundaryNorm(custom_levels, cmap_custom.N)

        p = ax.contourf(
        ds_4.longitude,
        ds_4.latitude,
        ds_4*3.6/1.852,
        transform=ccrs.PlateCarree(),
        cmap=cmap_custom,
        norm=norm_custom,
        levels=custom_levels,
        alpha=0.85
        )

        mslp_levels = np.arange(800, 1100, 2)
        cs = ax.contour(ds_mslp.longitude, ds_mslp.latitude, mslp_hpa,
                        levels=mslp_levels, colors='black', linewidths=0.85,
                        transform=ccrs.PlateCarree())
        ax.clabel(cs, inline=True, fontsize=10, fmt='%d')

        u_kts = ds_2.u * 3.6 / 1.852
        v_kts = ds_3.v * 3.6 / 1.852
        ax.barbs(ds_2.longitude, ds_2.latitude, u_kts, v_kts,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.9)

        ax.set_title(f'850hPa wind + MSLP(hPa)', fontsize=14)

        cb1 = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb1.set_label(f'knots', size='x-large')
        cb1.set_ticks([0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155])
        cb1.ax.tick_params(labelsize=12)

        valid_UTC = ds_2.valid_time.dt.strftime('%H:%M UTC %d %b %Y').item()
        valid_CST = (pd.to_datetime(ds_2.valid_time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = ds_2.time.dt.strftime('%H:%M UTC %d %b %Y').item()
        init_CST = (pd.to_datetime(ds_2.time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')

        fig.suptitle(
            f"GFS: 0.25 degree resolution\nValid: {valid_UTC} or {valid_CST}\ninitialized at {init_UTC} or {init_CST}\nforecast hour:{H.fxx}\nPlotted by GHMWS",
            color='red', fontsize=16
        )

        filename = f"{fxx}.png"
        save_full_path = os.path.join(save_path_6, filename)
        plt.savefig(save_full_path, dpi=150, bbox_inches='tight')
        plt.close(fig)  

        print("所有圖片已全部生成！")
        save_path_7= r"/Users/eknlau/VS_code/GHMWS-global-model/GFS/South China/850hPa wind"
        H = Herbie(run_str, model="gfs", product="pgrb2.0p25", fxx=fxx)

        ds_2 = H.xarray(":UGRD:850")
        ds_3 = H.xarray(":VGRD:850")
        ds_4 = mpcalc.wind_speed(ds_2.u, ds_3.v)
        ds_mslp = H.xarray("PRMSL")

        ds_2 = ds_2.sel(latitude=slice(90, 0,5), longitude=slice(90, 180,5))
        ds_3 = ds_3.sel(latitude=slice(90, 0,5), longitude=slice(90, 180,5))
        ds_4 = ds_4.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        ds_mslp = ds_mslp.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        mslp_hpa = ds_mslp.prmsl / 100

        fig, ax = plt.subplots(figsize=(14, 14), constrained_layout=True,
                               subplot_kw={'projection': ccrs.PlateCarree()})
        plot_background_2(ax)

        gradient_colors = [
            "#FFFFFF", "#F0F0F0", "#E0E0E0", "#D0D0D0",
            "#80FFFF", "#70EFEF", "#60DFDF", "#50CFCF", "#40BFBF", "#30AFAF",
            "#209F9F", "#108F8F", "#007F7F",
            "#009966", "#20A946", "#40B92C", "#60C912",
            "#80D900", "#A0E920", "#C0F940", "#E0FF60",
            "#FFFF80", "#FFE960", "#FFD340", "#FFBD20", "#FFA700",
            "#FF9100", "#FF7B00", "#FF6500", "#FF4F00", "#FF3900",
            "#990000", "#A91010", "#B92020", "#C93030", "#D94040",
            "#9900CC", "#A910D2", "#B920D8", "#C930DE", "#D940E4",
            "#E950EA", "#F960F0", "#FF70F6", "#FF80FC",
            "#FF90FC", "#FFA0F8", "#FFB0F4", "#FFC0F0", "#FFD0EC",
            "#FFE0E8", "#FFF0E4", "#FFFFE0",
            "#FFE0E0", "#FFD0D0", "#FFC0C0", "#FFB0B0", "#FFA0A0",
            "#FF9090", "#FF8080", "#FF7070", "#FF6060", "#FF5050",
            "#FF4040", "#FF3030", "#FF2020", "#FF1010", "#FF0000",
            "#E00000", "#D00000", "#C00000", "#B00000", "#A00000",
            "#900000", "#800000"
        ]
        cmap_custom = LinearSegmentedColormap.from_list("wind_smooth_original", gradient_colors, N=256)
        custom_levels = [0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155]
        norm_custom = BoundaryNorm(custom_levels, cmap_custom.N)

        p = ax.contourf(
        ds_4.longitude,
        ds_4.latitude,
        ds_4*3.6/1.852,
        transform=ccrs.PlateCarree(),
        cmap=cmap_custom,
        norm=norm_custom,
        levels=custom_levels,
        alpha=0.85
        )

        mslp_levels = np.arange(800, 1100, 2)
        cs = ax.contour(ds_mslp.longitude, ds_mslp.latitude, mslp_hpa,
                        levels=mslp_levels, colors='black', linewidths=0.85,
                        transform=ccrs.PlateCarree())
        ax.clabel(cs, inline=True, fontsize=10, fmt='%d')

        u_kts = ds_2.u * 3.6 / 1.852
        v_kts = ds_3.v * 3.6 / 1.852
        ax.barbs(ds_2.longitude, ds_2.latitude, u_kts, v_kts,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.9)

        ax.set_title(f'850hPa wind + MSLP(hPa)', fontsize=14)

        cb1 = fig.colorbar(p, ax=ax, orientation='horizontal')
        cb1.set_label(f'knots', size='x-large')
        cb1.set_ticks([0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155])
        cb1.ax.tick_params(labelsize=12)

        valid_UTC = ds_2.valid_time.dt.strftime('%H:%M UTC %d %b %Y').item()
        valid_CST = (pd.to_datetime(ds_2.valid_time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = ds_2.time.dt.strftime('%H:%M UTC %d %b %Y').item()
        init_CST = (pd.to_datetime(ds_2.time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')

        fig.suptitle(
            f"GFS: 0.25 degree resolution\nValid: {valid_UTC} or {valid_CST}\ninitialized at {init_UTC} or {init_CST}\nforecast hour:{H.fxx}\nPlotted by GHMWS",
            color='red', fontsize=16
        )

        filename = f"{fxx}.png"
        save_full_path = os.path.join(save_path_7, filename)
        plt.savefig(save_full_path, dpi=150, bbox_inches='tight')
        plt.close(fig)  

        print("所有圖片已全部生成！")
        save_path_8=r"/Users/eknlau/VS_code/GHMWS-global-model/GFS/South China/10m wind MSLP"
        print(f"Fetching {run_str} FXX {fxx}...")
        H = Herbie(run_str, model="gfs", product="pgrb2.0p25", fxx=fxx)
        ds_2 = H.xarray(":UGRD:10 m above_ground")
        ds_3 = H.xarray(":VGRD:10 m above_ground")
        ds_4 = mpcalc.wind_speed(ds_2.u10, ds_3.v10)
        ds_11 = H.xarray("PRMSL:")
        ds_2 = ds_2.sel(latitude=slice(90, 0,3), longitude=slice(90, 180,3))
        ds_3 = ds_3.sel(latitude=slice(90, 0,3), longitude=slice(90, 180,3))
        ds_4 = ds_4.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        ds_11 = ds_11.sel(latitude=slice(90, 0), longitude=slice(90, 180))
        fig, ax2 = plt.subplots(figsize=(12, 12), constrained_layout=True, subplot_kw={'projection': ccrs.PlateCarree()})
        plot_background_2(ax2)

        gradient_colors = [
            "#FFFFFF", "#F0F0F0", "#E0E0E0", "#D0D0D0",
            "#80FFFF", "#70EFEF", "#60DFDF", "#50CFCF", "#40BFBF", "#30AFAF",
            "#209F9F", "#108F8F", "#007F7F",
            "#009966", "#20A946", "#40B92C", "#60C912",
            "#80D900", "#A0E920", "#C0F940", "#E0FF60",
            "#FFFF80", "#FFE960", "#FFD340", "#FFBD20", "#FFA700",
            "#FF9100", "#FF7B00", "#FF6500", "#FF4F00", "#FF3900",
            "#990000", "#A91010", "#B92020", "#C93030", "#D94040",
            "#9900CC", "#A910D2", "#B920D8", "#C930DE", "#D940E4",
            "#E950EA", "#F960F0", "#FF70F6", "#FF80FC",
            "#FF90FC", "#FFA0F8", "#FFB0F4", "#FFC0F0", "#FFD0EC",
            "#FFE0E8", "#FFF0E4", "#FFFFE0",
            "#FFE0E0", "#FFD0D0", "#FFC0C0", "#FFB0B0", "#FFA0A0",
            "#FF9090", "#FF8080", "#FF7070", "#FF6060", "#FF5050",
            "#FF4040", "#FF3030", "#FF2020", "#FF1010", "#FF0000",
            "#E00000", "#D00000", "#C00000", "#B00000", "#A00000",
            "#900000", "#800000"
        ]
        cmap_custom = LinearSegmentedColormap.from_list("wind_smooth_original", gradient_colors, N=256)
        custom_levels = [0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155]
        norm_custom = BoundaryNorm(custom_levels, cmap_custom.N)

        p = ax2.contourf(
            ds_4.longitude,
            ds_4.latitude,
            ds_4*3.6/1.852,
            transform=ccrs.PlateCarree(),
            cmap=cmap_custom,
            norm=norm_custom,
            levels=custom_levels,
            alpha=0.85
        )

        u_kts = ds_2.u10 * 3.6 / 1.852
        v_kts = ds_3.v10 * 3.6 / 1.852
        ax2.barbs(ds_2.longitude, ds_2.latitude, u_kts, v_kts,
                 length=6, transform=ccrs.PlateCarree(), color='gray', linewidth=0.85)

        msl_contour = ax2.contour(
            ds_11.longitude,
            ds_11.latitude,
            ds_11.prmsl/100,
            levels=np.arange(800, 1100, 2),
            colors='black',
            transform=ccrs.PlateCarree()
        )

        ax2.clabel(msl_contour, fontsize=10, inline=1, inline_spacing=1, fmt='%i', rightside_up=True)

        ax2.set_title(f'10m wind + MSLP(hPa)', fontsize=14)
        cb1 = fig.colorbar(p, ax=ax2, orientation='horizontal')
        cb1.set_label(f'Knots', size='x-large')
        cb1.set_ticks([0,7,16,25,34,40,46,52,58,64,80,96,110,125,140,155])
        cb1.ax.tick_params(labelsize=12)

        valid_UTC = ds_2.valid_time.dt.strftime('%H:%M UTC %d %b %Y').item()
        valid_CST = (pd.to_datetime(ds_2.valid_time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')
        init_UTC = ds_2.time.dt.strftime('%H:%M UTC %d %b %Y').item()
        init_CST = (pd.to_datetime(ds_2.time.values) + pd.Timedelta(hours=8)).strftime('%H:%M CST/HKT/MST %d %b %Y')

        fig.suptitle(
            f"GFS: 0.25 degree resolution\nValid: {valid_UTC} or {valid_CST}\ninitialized at {init_UTC} or {init_CST}\nforecast hour:{fxx}\nPlotted by GHMWS",
            color='red', fontsize=16
        )

        save_full_path = os.path.join(save_path_8, f"{fxx}.png")
        plt.savefig(save_full_path, dpi=150, bbox_inches='tight')
        plt.close()

        print("所有圖片已全部生成！")

    except Exception as e:
        print(f"Error at FXX {fxx}: {e}")
        sys.exit(1) # Tell Shell script that data isn't ready yet

    print("Success")
sys.exit(0)