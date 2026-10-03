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

def get_herbie_params(model):
    """Helper to standardize model names, products, and search patterns."""
    model_lower = model.lower()
    
    if model_lower in ["gfs", "aigfs"]:
        herbie_model = "gfs"
        product = "pgrb2.0p25"
        patterns = {
            "hgt500": ":HGT:500 mb:",
            "mslp": ":PRMSL:mean sea level:",
            "u850": ":UGRD:850 mb:",
            "v850": ":VGRD:850 mb:",
            "u10": ":UGRD:10 m above ground:",
            "v10": ":VGRD:10 m above ground:",
            "t2m": ":TMP:2 m above ground:"
        }
    elif model_lower in ["ifs", "ecmwf"]:
        herbie_model = "ifs"
        product = "oper"
        patterns = {
            "hgt500": ":gh:500",
            "mslp": ":msl:",
            "u850": ":u:850",
            "v850": ":v:850",
            "u10": ":10u:",
            "v10": ":10v:",
            "t2m": ":2t:"
        }
    elif model_lower == "aifs":
        herbie_model = "aifs"
        product = "oper"
        patterns = {
            "hgt500": ":gh:500",
            "mslp": ":msl:",
            "u850": ":u:850",
            "v850": ":v:850",
            "u10": ":10u:",
            "v10": ":10v:",
            "t2m": ":2t:"
        }
    else:
        raise ValueError(f"Unsupported model: {model}")

    return herbie_model, product, patterns

def fetch_herbie_ds(model_name, product, fxx, search_pattern):
    """Wrapper to handle Herbie dataset queries."""
    H = Herbie(CYCLE_DATE, model=model_name, product=product, fxx=fxx)
    return H.xarray(search_pattern)

def extract_coords_and_grid(ds):
    """Ensures lons and lats are 2D arrays for uniform slicing."""
    data_var = list(ds.data_vars)[0]
    vals = ds[data_var].values.squeeze()
    
    lons = ds.longitude.values
    lats = ds.latitude.values

    if lons.ndim == 1 and lats.ndim == 1:
        lons, lats = np.meshgrid(lons, lats)
        
    return lons, lats, vals

# -------------------------------------------------------------
# 1. 500hPa Geopotential Height + MSLP Isobars
# -------------------------------------------------------------
def plot_500hpa_mslp(model="gfs", domain_key="east_asia", fxx=0):
    herbie_model, product, patterns = get_herbie_params(model)

    ds_hgt = fetch_herbie_ds(herbie_model, product, fxx, patterns["hgt500"])
    ds_mslp = fetch_herbie_ds(herbie_model, product, fxx, patterns["mslp"])

    lons, lats, hgt_vals = extract_coords_and_grid(ds_hgt)
    _, _, mslp_vals = extract_coords_and_grid(ds_mslp)

    hgt_dagpm = hgt_vals / 10.0 if hgt_vals.max() > 2000 else hgt_vals
    mslp_hpa = mslp_vals / 100.0 if mslp_vals.max() > 2000 else mslp_vals

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
    herbie_model, product, patterns = get_herbie_params(model)

    ds_u = fetch_herbie_ds(herbie_model, product, fxx, patterns["u850"])
    ds_v = fetch_herbie_ds(herbie_model, product, fxx, patterns["v850"])

    lons, lats, u = extract_coords_and_grid(ds_u)
    _, _, v = extract_coords_and_grid(ds_v)
    wind_kts = np.sqrt(u**2 + v**2) * 1.94384

    fig, ax = create_base_map(domain_key)
    cf = ax.contourf(lons, lats, wind_kts, levels=np.arange(10, 75, 5), cmap="YlGnBu", transform=ccrs.PlateCarree())
    plt.colorbar(cf, ax=ax, orientation="horizontal", pad=0.04, shrink=0.7, label="850hPa Wind Speed (kts)")

    skip = 3 if domain_key == "south_china" else 6
    ax.barbs(lons[::skip, ::skip], lats[::skip, ::skip], u[::skip, ::skip], v[::skip, ::skip], length=5, transform=ccrs.PlateCarree())

    plt.title(f"{model.upper()} | 850hPa Wind Vectors | {domain_key.upper()} | +{fxx:02d}h", fontsize=11, fontweight="bold")
    plt.savefig(f"{PLOTS_DIR}/{model}_850hpa_wind_{domain_key}_f{fxx:02d}.png", bbox_inches="tight")
    plt.close()

# -------------------------------------------------------------
# 3. 10m Surface Wind Vectors + MSLP Isobars
# -------------------------------------------------------------
def plot_10m_wind_mslp(model="gfs", domain_key="east_asia", fxx=0):
    herbie_model, product, patterns = get_herbie_params(model)

    ds_u10 = fetch_herbie_ds(herbie_model, product, fxx, patterns["u10"])
    ds_v10 = fetch_herbie_ds(herbie_model, product, fxx, patterns["v10"])
    ds_mslp = fetch_herbie_ds(herbie_model, product, fxx, patterns["mslp"])

    lons, lats, u10 = extract_coords_and_grid(ds_u10)
    _, _, v10 = extract_coords_and_grid(ds_v10)
    _, _, mslp_vals = extract_coords_and_grid(ds_mslp)

    mslp_hpa = mslp_vals / 100.0 if mslp_vals.max() > 2000 else mslp_vals
    wind10_kts = np.sqrt(u10**2 + v10**2) * 1.94384

    fig, ax = create_base_map(domain_key)
    cf = ax.contourf(lons, lats, wind10_kts, levels=np.arange(10, 65, 5), cmap="Spectral_r", transform=ccrs.PlateCarree())
    plt.colorbar(cf, ax=ax, orientation="horizontal", pad=0.04, shrink=0.7, label="10m Wind Speed (kts)")

    cs = ax.contour(lons, lats, mslp_hpa, levels=np.arange(960, 1048, 4), colors="black", linewidths=1.2, transform=ccrs.PlateCarree())
    ax.clabel(cs, inline=True, fontsize=8, fmt="%d")

    skip = 3 if domain_key == "south_china" else 6
    ax.barbs(lons[::skip, ::skip], lats[::skip, ::skip], u10[::skip, ::skip], v10[::skip, ::skip], length=4.5, transform=ccrs.PlateCarree())

    plt.title(f"{model.upper()} | 10m Wind + MSLP | {domain_key.upper()} | +{fxx:02d}h", fontsize=11, fontweight="bold")
    plt.savefig(f"{PLOTS_DIR}/{model}_10m_wind_mslp_{domain_key}_f{fxx:02d}.png", bbox_inches="tight")
    plt.close()

# -------------------------------------------------------------
# 4. 2m Temperature + MSLP Isobars
# -------------------------------------------------------------
def plot_2m_temp(model="gfs", domain_key="east_asia", fxx=0):
    herbie_model, product, patterns = get_herbie_params(model)

    ds_t2m = fetch_herbie_ds(herbie_model, product, fxx, patterns["t2m"])
    ds_mslp = fetch_herbie_ds(herbie_model, product, fxx, patterns["mslp"])

    lons, lats, t2m_vals = extract_coords_and_grid(ds_t2m)
    _, _, mslp_vals = extract_coords_and_grid(ds_mslp)

    # Convert Kelvin to Celsius if necessary
    t2m_c = t2m_vals - 273.15 if t2m_vals.max() > 150 else t2m_vals
    mslp_hpa = mslp_vals / 100.0 if mslp_vals.max() > 2000 else mslp_vals

    fig, ax = create_base_map(domain_key)
    cf = ax.contourf(lons, lats, t2m_c, levels=np.arange(-10, 42, 2), cmap="coolwarm", transform=ccrs.PlateCarree(), extend="both")
    plt.colorbar(cf, ax=ax, orientation="horizontal", pad=0.04, shrink=0.7, label="2m Temperature (°C)")

    cs = ax.contour(lons, lats, mslp_hpa, levels=np.arange(960, 1048, 4), colors="black", linewidths=1.0, transform=ccrs.PlateCarree())
    ax.clabel(cs, inline=True, fontsize=8, fmt="%d")

    plt.title(f"{model.upper()} | 2m Temperature + MSLP | {domain_key.upper()} | +{fxx:02d}h", fontsize=11, fontweight="bold")
    plt.savefig(f"{PLOTS_DIR}/{model}_2m_temp_{domain_key}_f{fxx:02d}.png", bbox_inches="tight")
    plt.close()

# -------------------------------------------------------------
# BATCH EXECUTION MATRIX
# -------------------------------------------------------------
if __name__ == "__main__":
    MODELS = ["ifs", "aifs", "gfs"]
    DOMAINS_TO_RUN = ["south_china", "east_asia", "nw_pacific"]
    
    # 0 to 180 hours every 6 hours (31 forecast steps: 00h to 180h)
    FORECAST_HOURS = list(range(0, 121, 6)) + list(range(132, 229, 12))

    for model in MODELS:
        for domain in DOMAINS_TO_RUN:
            for fxx in FORECAST_HOURS:
                try:
                    plot_500hpa_mslp(model=model, domain_key=domain, fxx=fxx)
                    plot_850hpa_wind(model=model, domain_key=domain, fxx=fxx)
                    plot_10m_wind_mslp(model=model, domain_key=domain, fxx=fxx)
                    plot_2m_temp(model=model, domain_key=domain, fxx=fxx)
                except Exception as e:
                    print(f"Error {model} {domain} f{fxx:02d}: {e}")