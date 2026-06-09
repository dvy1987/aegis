"use client";

import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

// NOTE: DrawSVGPlugin is a paid Club GreenSock plugin and is NOT in the public
// `gsap` npm package — importing it breaks the build. SVG path-draw in the
// showcase is done with framer-motion's `pathLength` instead. Only the free
// ScrollTrigger plugin is registered here.
gsap.registerPlugin(ScrollTrigger);

export { gsap, ScrollTrigger };
