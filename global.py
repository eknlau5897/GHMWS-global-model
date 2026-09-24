import os
import datetime
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from herbie import Herbie

PLOTS_DIR = "plots"
os.makedirs(PLOTS_DIR, exist_ok=True)

# Select recent UTC run time
CYCLE_DATE = (datetime.datetime.utcnow() - datetime.timedelta(days=1)).strftime("%Y-%m-%d 12:00")

# Geographic Domains [West, East, South, North]
DOMAINS = {
    "south_china": [105, 122, 18, 26],   # Guangdong, Hong Kong, Macao, Taiwan Strait
    "east_asia": [95, 145, 15, 55],      # China, Japan, Korea, Philippines
    "nw_pacific": [105, 165, 20, 60]     # Broader Typhoon/Synoptic Domain
}

def create_base_map(domain_key):
    """Generates standard Cartopy plot layout configured for chosen domain."""
    fig = plt.figure(figsize=(12, 9), dpi=150)
    ax = plt.axes(projection=ccrs.PlateCarree())
    extent = DOMAINS[domain_key]
    ax.set_extent(extent, crs=ccrs.PlateCarree())

    # Map details scaling
    scale = "10m" if domain_key == "south_china" else "50m"
    ax.add_feature(cfeature.COASTLINE.with_scale(scale), linewidth=0.8, edgecolor="black")
    ax.add_feature(cfeature.BORDERS.with_scale(scale), linewidth=0.5, edgecolor="black")

    gl = ax.gridlines(draw_labels=True, linewidth=0.3, color='gray', alpha=0.5, linestyle='--')
    gl.top_labels, gl.right_labels = False, True
    return fig, ax

def fetch_herbie_ds(model, product, fxx, search_pattern):
    """Wrapper to handle Herbie dataset queries."""
    H = Herbie(CYCLE_DATE, model=model, product=product, fxx=fxx)
    return H.xarray(search_pattern)

# -------------------------------------------------------------
# 1. 500hPa Geopotential Height + MSLP Isobars
# -------------------------------------------------------------
def plot_500hpa_mslp(model="gfs", domain_key="east_asia", fxx=0):
    product = "pgrb2.0p25" if model in ["gfs", "aigfs"] else "ifs"
    hgt_pat = ":HGT:500 mb:" if model in ["gfs", "aigfs"] else ":gh:500:"
    mslp_pat = ":PRMSL:mean sea level:" if model in ["gfs", "aigfs"] else ":msl:"

    ds_hgt = fetch_herbie_ds(model, product, fxx, hgt_pat)
    ds_mslp = fetch_herbie_ds(model, product, fxx, mslp_pat)

    lons, lats = ds_hgt.longitude.values, ds_hgt.latitude.values
    hgt_dagpm = ds_hgt[list(ds_hgt.data_vars)[0]].values / 10.0
    mslp_hpa = ds_mslp[list(ds_mslp.data_vars)[0]].values / 100.0

    fig, ax = create_base_map(domain_key)
    ax.contourf(lons, lats, hgt_dagpm, levels=np.arange(500, 600, 4), cmap="YlOrRd", transform=ccrs.PlateCarree())
    cs = ax.contour(lons, lats, mslp_hpa, levels=np.arange(960, 1048, 4), colors="black", linewidths=1.0, transform=ccrs.PlateCarree())
    ax.clabel(cs, inline=True, fontsize=8, fmt="%d")

    plt.title(f"{model.upper()} | 500hPa HGT + MSLP | {domain_key.upper()} | +{fxx:02d}h", fontsize=11, color="#b91c1c", fontweight="bold")
    plt.savefig(f"{PLOTS_DIR}/{model}_500hpa_mslp_{domain_key}_f{fxx:02d}.png", bbox_inches="tight")
    plt.close()

# -------------------------------------------------------------
# 2. 850hPa Wind Speed & Wind Vectors
# -------------------------------------------------------------
def plot_850hpa_wind(model="gfs", domain_key="east_asia", fxx=0):
    product = "pgrb2.0p25" if model in ["gfs", "aigfs"] else "ifs"
    u_pat = ":UGRD:850 mb:" if model in ["gfs", "aigfs"] else ":u:850:"
    v_pat = ":VGRD:850 mb:" if model in ["gfs", "aigfs"] else ":v:850:"

    ds_u = fetch_herbie_ds(model, product, fxx, u_pat)
    ds_v = fetch_herbie_ds(model, product, fxx, v_pat)

    lons, lats = ds_u.longitude.values, ds_u.latitude.values
    u, v = ds_u[list(ds_u.data_vars)[0]].values, ds_v[list(ds_v.data_vars)[0]].values
    wind_kts = np.sqrt(u**2 + v**2) * 1.94384

    fig, ax = create_base_map(domain_key)
    cf = ax.contourf(lons, lats, wind_kts, levels=np.arange(10, 75, 5), cmap="YlGnBu", transform=ccrs.PlateCarree())
    plt.colorbar(cf, ax=ax, orientation="horizontal", pad=0.04, shrink=0.7, label="850hPa Wind Speed (kts)")

    skip = 3 if domain_key == "south_china" else 6
    ax.barbs(lons[::skip], lats[::skip], u[::skip, ::skip], v[::skip, ::skip], length=5, transform=ccrs.PlateCarree())

    plt.title(f"{model.upper()} | 850hPa Wind Vectors | {domain_key.upper()} | +{fxx:02d}h", fontsize=11, fontweight="bold")
    plt.savefig(f"{PLOTS_DIR}/{model}_850hpa_wind_{domain_key}_f{fxx:02d}.png", bbox_inches="tight")
    plt.close()

# -------------------------------------------------------------
# 3. 10m Surface Wind Vectors + MSLP Isobars
# -------------------------------------------------------------
def plot_10m_wind_mslp(model="gfs", domain_key="east_asia", fxx=0):
    product = "pgrb2.0p25" if model in ["gfs", "aigfs"] else "ifs"
    u10_pat = ":UGRD:10 m above ground:" if model in ["gfs", "aigfs"] else ":10u:"
    v10_pat = ":VGRD:10 m above ground:" if model in ["gfs", "aigfs"] else ":10v:"
    mslp_pat = ":PRMSL:mean sea level:" if model in ["gfs", "aigfs"] else ":msl:"

    ds_u10 = fetch_herbie_ds(model, product, fxx, u10_pat)
    ds_v10 = fetch_herbie_ds(model, product, fxx, v10_pat)
    ds_mslp = fetch_herbie_ds(model, product, fxx, mslp_pat)

    lons, lats = ds_u10.longitude.values, ds_u10.latitude.values
    u10, v10 = ds_u10[list(ds_u10.data_vars)[0]].values, ds_v10[list(ds_v10.data_vars)[0]].values
    mslp_hpa = ds_mslp[list(ds_mslp.data_vars)[0]].values / 100.0
    wind10_kts = np.sqrt(u10**2 + v10**2) * 1.94384

    fig, ax = create_base_map(domain_key)
    # Wind speed heatmap
    cf = ax.contourf(lons, lats, wind10_kts, levels=np.arange(10, 65, 5), cmap="Spectral_r", transform=ccrs.PlateCarree())
    plt.colorbar(cf, ax=ax, orientation="horizontal", pad=0.04, shrink=0.7, label="10m Wind Speed (kts)")

    # MSLP Isobar contours
    cs = ax.contour(lons, lats, mslp_hpa, levels=np.arange(960, 1048, 4), colors="black", linewidths=1.2, transform=ccrs.PlateCarree())
    ax.clabel(cs, inline=True, fontsize=8, fmt="%d")

    # Wind barbs overlay
    skip = 3 if domain_key == "south_china" else 6
    ax.barbs(lons[::skip], lats[::skip], u10[::skip, ::skip], v10[::skip, ::skip], length=4.5, transform=ccrs.PlateCarree())

    plt.title(f"{model.upper()} | 10m Wind + MSLP | {domain_key.upper()} | +{fxx:02d}h", fontsize=11, fontweight="bold")
    plt.savefig(f"{PLOTS_DIR}/{model}_10m_wind_mslp_{domain_key}_f{fxx:02d}.png", bbox_inches="tight")
    plt.close()

# -------------------------------------------------------------
# BATCH EXECUTION MATRIX
# -------------------------------------------------------------
if __name__ == "__main__":
    MODELS = ["ecmwf", "aifs", "gfs", "aigfs"]
    DOMAINS_TO_RUN = ["south_china", "east_asia", "nw_pacific"]
    FORECAST_HOURS = [0, 12, 24, 36, 48, 60, 72, 84, 96, 108, 120, 132, 144, 156, 168, 180, 192, 204, 216, 228, 240]

    for model in MODELS:
        for domain in DOMAINS_TO_RUN:
            for fxx in FORECAST_HOURS:
                try:
                    plot_500hpa_mslp(model=model, domain_key=domain, fxx=fxx)
                    plot_850hpa_wind(model=model, domain_key=domain, fxx=fxx)
                    plot_10m_wind_mslp(model=model, domain_key=domain, fxx=fxx)
                except Exception as e:
                    print(f"Error {model} {domain} f{fxx}: {e}")