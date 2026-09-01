# SafeNest competition sensor node

The Arduino sketch in this directory collects the integrated SafeNest sensor
data and streams it to the Raspberry Pi runtime over Wi-Fi/TCP.

Before uploading the sketch, copy `secrets.example.h` to `secrets.h` locally
and configure the Wi-Fi credentials and Raspberry Pi address. `secrets.h` is
ignored by the repository and must not be committed.

The matching receiver and dashboard live in
`ondevice_ai/integrated_node/competition_runtime/`. Setup and communication
guides live in `docs/competition_runtime/`.
