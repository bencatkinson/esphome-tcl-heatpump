#!/usr/bin/env python3
"""Host test for the decoder lambda in packages/tcl-decoder.yaml.

Pulls the uart debug lambda out of the package, wraps it in small stand-ins for
the ESPHome classes, compiles it with g++ and feeds it synthetic frames.
Run: python3 tests/host_test.py   (needs g++ and PyYAML)
"""
import pathlib
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Loader(yaml.SafeLoader):
    pass


Loader.add_constructor("!lambda", lambda l, n: l.construct_scalar(n))

pkg = yaml.load((ROOT / "packages/tcl-decoder.yaml").read_text(), Loader=Loader)
subs = pkg["substitutions"]
body = pkg["uart"]["debug"]["sequence"][0]["lambda"]
for k, v in subs.items():
    body = body.replace("${%s}" % k, str(v))

ids = {}
for kind, cls in (("sensor", "sensor::Sensor"), ("binary_sensor", "binary_sensor::BinarySensor"),
                  ("text_sensor", "text_sensor::TextSensor")):
    for e in pkg[kind]:
        ids[e["id"]] = cls

decls = "\n".join(f"{cls} {i}_obj; {cls}* {i} = &{i}_obj;" for i, cls in ids.items())

CPP = r"""
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
#include <map>
// Arduino core macros that clash with common helper names
#define bit(b) (1UL << (b))
static uint32_t fake_ms = 100000;
uint32_t millis() { return fake_ms; }
namespace sensor { struct Sensor { float state = NAN; int n = 0; void publish_state(float v) { state = v; n++; } }; }
namespace binary_sensor { struct BinarySensor { bool state = false, has = false; bool has_state() { return has; } void publish_state(bool v) { state = v; has = true; } }; }
namespace text_sensor { struct TextSensor { std::string state; bool has = false; bool has_state() { return has; } void publish_state(const std::string &v) { state = v; has = true; } }; }
struct Script { int n = 0; void execute() { n++; } };
std::vector<uint8_t> tcl_rx_buf_v; uint32_t tcl_last_status_ms_v = 0, tcl_energy_last_query_ms_v = 0, tcl_energy_prev_ms_v = 0;
double tcl_energy_prev_kwh_v = NAN, tcl_energy_step_kwh_v = 0; float tcl_energy_rate_w_v = NAN; int tcl_compressor_hz_v = -1;
Script tcl_energy_request_v;
#define tcl_rx_buf (&tcl_rx_buf_v)
#define tcl_last_status_ms (&tcl_last_status_ms_v)
#define tcl_energy_last_query_ms (&tcl_energy_last_query_ms_v)
#define tcl_energy_prev_ms (&tcl_energy_prev_ms_v)
#define tcl_energy_prev_kwh (&tcl_energy_prev_kwh_v)
#define tcl_energy_step_kwh (&tcl_energy_step_kwh_v)
#define tcl_energy_rate_w (&tcl_energy_rate_w_v)
#define tcl_compressor_hz (&tcl_compressor_hz_v)
#define tcl_energy_request (&tcl_energy_request_v)
template <typename T> T &id_ref(T *p) { return *p; }
template <typename T> T *id_ptr(T *p) { return p; }
DECLS
// Globals are references in ESPHome's id(); sensors are pointers.
template <typename T> struct IdSel { static T *get(T *p) { return p; } };
#define id(x) ID_##x
IDMAP
void decode(const std::vector<uint8_t> &bytes) {
BODY
}
static int fails = 0;
#define CHECK(c) do { if (!(c)) { printf("FAIL line %d: %s\n", __LINE__, #c); fails++; } } while (0)
#define NEAR(a, b) CHECK(std::fabs((a) - (b)) < 1e-3)
std::vector<uint8_t> frame(uint8_t cmd, std::vector<uint8_t> payload) {
  std::vector<uint8_t> f = {0xBB, 0x01, 0x00, cmd, (uint8_t) payload.size()};
  f.insert(f.end(), payload.begin(), payload.end());
  uint8_t x = 0; for (auto b : f) x ^= b; f.push_back(x); return f;
}
int main() {
  std::vector<uint8_t> p(55, 0);
  auto F = [&](int i, uint8_t v) { p[i - 5] = v; };
  F(7, 0x10 | 0x04);          // power on, heat
  F(8, 0x05);                 // 21 + 0.5
  F(9, 0x02);
  int room = 200 + 213;       // 21.3 C
  F(17, room >> 2); F(18, (room & 3) << 2);        // bit5 clear -> A
  F(30, 110);                 // 0.4*110-20 = 24
  F(34, 3); F(35, 32); F(36, 28); F(37, 75); F(38, 42); F(39, 5);
  F(45, 0xE6);                // 230 V
  F(46, 17);
  F(50, 0x02);                // filter blocked
  F(41, 0x02);                // error code 2
  F(56, 0x81);                // masked group: no code 27
  F(58, 0x01);                // code 41
  auto f = frame(0x04, p);
  // split across two debug callbacks, with leading junk
  std::vector<uint8_t> a = {0x00, 0x12}; a.insert(a.end(), f.begin(), f.begin() + 20);
  std::vector<uint8_t> b(f.begin() + 20, f.end());
  decode(a); decode(b);
  NEAR(hp_room_temp->state, 21.3f);
  NEAR(hp_target_temperature_exact->state, 21.5f);
  NEAR(hp_byte30_a->state, 24.0f);
  CHECK(std::isnan(hp_byte30_b->state));
  NEAR(hp_outdoor_temp->state, 12); NEAR(hp_outdoor_coil_temp->state, 8); NEAR(hp_discharge_temp->state, 55);
  NEAR(hp_compressor_freq->state, 42); CHECK(hp_compressor_running->state);
  NEAR(hp_supply_voltage->state, 230); NEAR(hp_load_index->state, 17);
  CHECK(hp_filter_blocked->state); CHECK(!hp_filter_alarm_enabled->state);
  CHECK(hp_error_codes->state == "2,41"); CHECK(hp_fault->state);
  CHECK(tcl_energy_request_v.n == 1);
  // voltage wrap and byte 30 B
  F(45, 4); F(18, 0x20 | ((room & 3) << 2)); F(30, 100); F(41, 0); F(58, 0);
  decode(frame(0x04, p));
  NEAR(hp_supply_voltage->state, 260); NEAR(hp_byte30_b->state, 20.0f); NEAR(hp_byte30_a->state, 24.0f);
  CHECK(hp_error_codes->state == "none"); CHECK(!hp_fault->state);
  // bad checksum ignored
  auto bad = frame(0x04, p); bad[30] ^= 0xFF; F(38, 0); decode(bad);
  NEAR(hp_compressor_freq->state, 42);
  // energy reply: 1234.567891 kWh
  std::vector<uint8_t> e(30, 0);
  auto E = [&](int i, uint8_t v) { e[i - 5] = v; };
  E(7, 0x0C); E(11, 0x00); E(10, 0x12); E(9, 0x34); E(8, 0x56); E(21, 0x78); E(20, 0x91);
  decode(frame(0x0A, e));
  NEAR(hp_energy->state, 1234.567891f);
  fake_ms += 60000;
  E(8, 0x57);  // +0.01 kWh in 60 s = 600 W
  decode(frame(0x0A, e));
  NEAR(tcl_energy_rate_w_v, 600.0f);
  // module-to-unit frames ignored
  auto tx = frame(0x0A, e); tx[1] = 0x00; tx[2] = 0x01; tx.back() = 0; { uint8_t x = 0; for (size_t i = 0; i + 1 < tx.size(); i++) x ^= tx[i]; tx.back() = x; }
  E(8, 0x99); decode(tx);
  NEAR(tcl_energy_rate_w_v, 600.0f);
  printf("%s\n", fails ? "FAILED" : "all decoder checks passed");
  return fails != 0;
}
"""

# Mirror ESPHome's lambda rewriting: id(global) -> its value, id(component).f -> ptr->f,
# id(component) -> pointer.
import re
globals_ = {g["id"] for g in pkg["globals"]}
def rewrite(m):
    name, dot = m.group(1), m.group(2)
    if name in globals_:
        return f"(*{name})" + dot
    return name + ("->" if dot else "")
body = re.sub(r"id\((\w+)\)(\.?)", rewrite, body)
src = CPP.replace("DECLS", decls).replace("IDMAP", "").replace("BODY", body)
src = src.replace("#define id(x) ID_##x", "")
with tempfile.TemporaryDirectory() as d:
    c = pathlib.Path(d) / "t.cpp"
    c.write_text(src)
    exe = pathlib.Path(d) / "t"
    r = subprocess.run(["g++", "-std=gnu++17", "-Wall", "-Wno-unused", "-o", str(exe), str(c)],
                       capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[:4000])
        sys.exit(1)
    sys.exit(subprocess.run([str(exe)]).returncode)
