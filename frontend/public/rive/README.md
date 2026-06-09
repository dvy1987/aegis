# Showcase Rive placeholders

Temporary `.riv` assets for wiring the `/showcase` cinematic redesign. **Replace with custom Aegis art from the [Rive editor](https://rive.app) before the final demo.**

## Source

Copied from the official open-source examples in [rive-app/rive-wasm](https://github.com/rive-app/rive-wasm/tree/master/wasm/examples/parcel_example) (`master` branch).

## Files

| Repo file | Upstream sample | Planned use | Match quality |
|---|---|---|---|
| `glyph.riv` | `hero-v6.riv` | Act I hero living glyph | Decent placeholder — not Aegis-branded |
| `memory-toggle.riv` | `switch_event_example.riv` | Act V memory on/off toggle | **Good** — switch + state machine |
| `lift-gauge.riv` | `rating_animation.riv` | Act IV lift counter / gauge | **Good** — value-driven fill |
| `status-orb.riv` | `look.riv` | Act III run status orb | Weak — avatar idle, not multi-state orb |
| `pipeline-icons.riv` | `message_icon.riv` | Act V pipeline node marks | Weak — single tiny icon |

## Not included (no good open-source match)

- `button-ignite.riv` — use CSS/framer until custom art exists
- `verdict-cell.riv` — plan prefers CSS/GSAP cascade for grid cells

## State machines

These placeholders use Rive’s default artboard/state names from the upstream samples (e.g. `"Main State Machine"` on the switch). The showcase plan expects custom inputs (`breath`, `ignite`, `runStatus`, `memoryOn`, etc.) — wire to these only after final assets ship.

## License

Rive runtime and sample files follow Rive’s licensing. See [rive.app](https://rive.app) and the upstream repo for terms.
