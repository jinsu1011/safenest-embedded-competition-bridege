# Competition runtime

This directory contains the Raspberry Pi runtime from `SafeNest_GitHub_Package`.

- `raspberry_pi_lcd/`: ESP32 TCP receiver, LCD pages, thermal view, and GPIO buzzer control
- `SafeNest_Web/`: administrator and guest web dashboard with the Raspberry Pi bridge
- `install_raspberry_pi.sh`: installs both runtime applications into the Raspberry Pi home directory
- `start_all.sh`: starts the LCD receiver and web dashboard

Related files:

- ESP32 sketch: `devices/mmwave/firmware/competition_sensor_node/`
- Setup and protocol documentation: `docs/competition_runtime/`

Copy `SafeNest_Web/.env.example` to `.env` and
`devices/mmwave/firmware/competition_sensor_node/secrets.example.h` to `secrets.h`
only on the target machine. Never commit the resulting secret files.
