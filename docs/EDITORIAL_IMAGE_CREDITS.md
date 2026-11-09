# Editorial images — origin and deployment notes

The v6 visual redesign uses **original website layout/code**, not copied HTML, CSS, layouts or brand assets from Visit Dubai, GetYourGuide or Tripadvisor. Sites were reviewed for general UX practices such as discovery-first navigation, photography-led cards, and clear user journeys.

Images shown by the redesigned pages are requested from Unsplash CDN (`images.unsplash.com`). They are **not embedded in the ZIP**, so a network connection to the CDN is required; if the CDN fails, the app shows a neutral destination-themed gradient rather than a photo from the wrong city. The hero alone uses an existing local image from the project as a fallback. Image credit links are provided here for source review and optional attribution:

| Website usage | Photographer/source link | Source photo id |
|---|---|---|
| Giza pyramids / hero | https://unsplash.com/photos/three-pyramids-in-the-desert-with-a-blue-sky-in-the-background-OVofPjTSfOQ | photo-1678747365851-2f2ebb09911d |
| Cairo / Nile | https://unsplash.com/photos/felucca-on-nile-river-in-cairo-59RY-ykUIAg | photo-1719659018185-8a239c35fb4a |
| Karnak / Luxor | https://unsplash.com/s/photos/karnak | photo-1609101652237-b4704a00bc50 |
| Aswan / felucca | https://unsplash.com/photos/a-sailboat-in-a-body-of-water-with-a-mountain-in-the-background-7ObNCbySGGc | photo-1644517270263-4112379d97ca |
| Hurghada / Red Sea | https://unsplash.com/photos/an-aerial-view-of-an-island-in-the-middle-of-the-ocean-EitGuBFJ7l0 | photo-1722264221977-3a933a891199 |
| Alexandria / Qaitbay | https://unsplash.com/photos/a-stone-castle-with-a-flag-on-top-of-it-sp22OCGxjho | photo-1682090500311-9e57a5a57390 |
| Siwa Oasis | https://unsplash.com/photos/ariel-view-of-a-desert-town-with-palm-trees-W5gcPF6A9c4 | photo-1771838877341-36157f26dd58 |
| Sinai / Dahab-Nuweiba coastline | https://unsplash.com/photos/a-group-of-people-on-a-beach-FwXkH-wHR9s | photo-1666593198332-127af3e3536d |

**Licensing and operational note:** Images appeared on source pages as free to use under the Unsplash License at review time (Oct 2026). Review the current [Unsplash License](https://unsplash.com/license) and each individual photo page again before a commercial launch. Do not imply partnership with Unsplash or the source websites. Replace remote image hotlinks with properly authorized/self-hosted optimized assets before a high-traffic launch to improve stability. Images originally included in the project (`gem.jpeg`, `hieroglyphics.jpeg`, etc.) retain their original source/license obligations; confirm provenance before commercial use.
