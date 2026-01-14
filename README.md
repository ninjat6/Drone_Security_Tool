# UAV Security Tool

## How to run GUI

### Option A: Using uv (Recommended)

1. Install uv: Refer to [uv official document](https://docs.astral.sh/uv/getting-started/installation/)

2. Create virtual environment and install dependencies:

```bash
uv sync
```

3. Run the application:

```bash
uv run ./src/gui/main_window.py
```

### Option B: Using pip

1. Create virtual environment:

```bash
python -m venv .venv
```

2. Activate virtual environment:

```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -e .
```

4. Run the application:

```bash
python ./src/gui/main_window.py
```

---

# HackRF

## Updating Firmware

1. Download the last release [HackRF Releases](https://github.com/greatscottgadgets/hackrf/releases).
2. connect HackRF to your computer via USB.
3. Open terminal and navigate to the folder where you downloaded the repostory.
4. Run the following command to update the firmware:

```
cd firmware-bin
hackrf_spiflash -w hackrf_one_usb.bin
```

## Installation HackRF Software form source

1. Open terminal and navigate to the folder where you downloaded the repostory.
2. Run the following command to install the software:

```
cd hackrf/host
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
```

3. Verify the installation by running:

```
hackrf_info
```

---

## Third-Party Installation

### gps-sdr-sim

1. Download the gps-sdr-sim from GitHub:

```
# if repo not in third_party folder, run:
cd third_party
git clone https://github.com/osqzss/gps-sdr-sim.git
```

2. Build gps-sdr-sim:

```
cd gps-sdr-sim
gcc gpssim.c -lm -O3 -o gps-sdr-sim
```

3. Verify the installation by running:

```
./gps-sdr-sim -h
```

---

## requirements

### Ubuntu

```
sudo apt update
sudo apt install -y \
    gnuradio \
    gr-osmosdr \
    hackrf \
```

```
sudo apt install fcitx-frontend-qt6
sudo apt install libxcb-cursor0
```

### python dependencies

```
pip install --upgrade pip
```
