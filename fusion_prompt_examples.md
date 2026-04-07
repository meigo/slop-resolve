# Fusion Graph Prompt Examples

Example prompts you can use with the Resolve AI Agent to create and modify Fusion compositions.

---

## Basic Node Setups

### Background with Text
```
Add a Fusion composition to the current timeline. Create a Background node set to solid dark blue (#1a1a2e), connect it to a Text+ node that says "Chapter One" in white, centered, using a clean sans-serif font at size 0.1. Merge them together and connect to MediaOut.
```

### Simple Lower Third
```
Create a Fusion comp lower third: a rounded rectangle background in semi-transparent black positioned at the bottom of the frame, with white Text+ on top saying "John Smith - Director". Add a 1-second fade in and fade out using opacity animation on the Merge node.
```

### Picture-in-Picture
```
On the current Fusion comp, take MediaIn1 and resize it to 30% scale, position it in the top-right corner with a 2px white border. Merge it over MediaIn2 as the full-screen background.
```

---

## Motion Graphics

### Animated Title Card
```
Build a Fusion title comp: Start with a black background. Add a white horizontal line that animates from zero width to full screen width over 20 frames. Then have Text+ reading "THE BEGINNING" fade in above the line over the next 15 frames. Use keyframes on the size and blend.
```

### Logo Reveal with Glow
```
Create a Fusion comp that loads my logo from the media pool, adds a Glow node with intensity 0.5, then animates the logo scaling from 0 to 1 over 30 frames with an ease-in-out curve. Put a solid black Background behind it.
```

### Scrolling Credits
```
Set up a Fusion composition for end credits. Use a Text+ node with the following names, one per line: "Director: Jane Doe", "Producer: Alex Smith", "Editor: Sam Lee". Animate the text scrolling upward from below the frame to above it over 200 frames against a black background.
```

### Countdown Timer
```
Create a Fusion comp with a 5-second countdown. Use a Text+ node that displays numbers 5, 4, 3, 2, 1 using keyframed StyledText, with each number visible for 1 second. Center the text on a dark gray background. Add a Circle mask that shrinks with each count.
```

---

## Color and Effects

### Vignette Effect
```
Add a Fusion comp to the selected clip. Take MediaIn1, apply an elliptical gradient background in black with soft edges, and multiply it over the footage using a Merge node to create a vignette effect. Set the vignette softness to about 0.4.
```

### Duotone / Color Grade Look
```
In the current Fusion comp, take MediaIn1 and add a Color Corrector node. Desaturate the image fully, then add a second Color Corrector that maps shadows to deep teal (#003344) and highlights to warm orange (#ff8844). Connect to MediaOut.
```

### Lens Blur / Bokeh
```
On the selected clip's Fusion comp, add a Blur node to MediaIn1 with a blur size of 10. Use an elliptical mask on the Blur to keep the center of the frame sharp and blur only the edges, simulating a tilt-shift or shallow depth of field look.
```

### Film Grain Overlay
```
Create a Fusion comp that adds film grain to the current clip. Use a FastNoise node set to a fine grain pattern, lower its blend opacity to 0.15, and merge it over MediaIn1 using a Soft Light blend mode.
```

---

## Compositing

### Green Screen Keying
```
Set up a Fusion comp for green screen removal on the current clip. Take MediaIn1, add a Delta Keyer node, and set the key color to green. Clean up the matte with an Erode/Dilate and a Blur on the garbage matte. Merge the keyed foreground over a Background node set to solid gray so I can check the key quality.
```

### Split Screen (Two Sources)
```
Create a Fusion comp with a vertical split screen. Take MediaIn1 for the left half and MediaIn2 for the right half. Use rectangular masks to crop each to 50% width. Merge them side by side on a black background. Add a thin 3px white divider line in the center.
```

### Reflection Effect
```
Take MediaIn1 in the current Fusion comp, duplicate it with a Transform node that flips it vertically and positions it below the original. Reduce the opacity of the reflection to 0.3 and add a gradient mask that fades it out toward the bottom. Merge both over a dark background.
```

### Day-to-Night Conversion
```
On this clip's Fusion comp, take MediaIn1 and add a Color Corrector. Bring down the gain significantly, push the midtones toward blue, and desaturate slightly. Then add a highlight suppression to knock down any hot spots. This should simulate a moonlit night look.
```

---

## Shapes and Overlays

### Animated Subscribe Button
```
Build a Fusion comp with a rounded red rectangle (#cc0000) positioned at bottom-right. Add white Text+ reading "SUBSCRIBE" inside it. Animate it sliding in from the right side over 15 frames, hold for 3 seconds, then slide back out over 15 frames.
```

### Progress Bar
```
Create a Fusion comp with a thin horizontal progress bar at the bottom of the frame. Use a dark gray rectangle as the track and a bright blue (#0088ff) rectangle as the fill. Animate the fill width from 0% to 100% over the duration of the comp.
```

### Callout / Annotation Arrow
```
In a new Fusion comp, create a line shape from coordinates (0.3, 0.5) to (0.6, 0.3) to act as a pointer arrow. Add a small rounded rectangle at the end point with Text+ inside reading "Important Detail". Animate the line drawing on over 15 frames, then pop the label in.
```

### Corner Bug / Watermark
```
Add a Fusion comp to the current clip that places a semi-transparent white Text+ reading "PREVIEW" in the top-right corner at 0.03 size and 0.25 opacity. Make sure it stays fixed regardless of any other transforms on the footage.
```

---

## Transitions (Fusion Transitions)

### Cross Dissolve with Blur
```
Create a Fusion transition comp. Take the outgoing clip and the incoming clip, apply an increasing blur to the outgoing clip while dissolving to the incoming clip over 30 frames. Use Merge with animated blend.
```

### Wipe with Shape Mask
```
Build a Fusion transition that uses an animated circular mask expanding from the center. The incoming clip is revealed through the expanding circle while the outgoing clip stays in the background. Animate the mask size from 0 to full coverage over 20 frames.
```

### Glitch Transition
```
Create a Fusion transition comp. On the outgoing clip, add horizontal offset displacement using a Transform node that randomly shifts the image left and right over 10 frames. Dissolve into the incoming clip during the glitch. Add a FastNoise-based RGB channel offset for extra glitch feel.
```

---

## Particle and 3D

### Particle Emitter Background
```
Set up a Fusion comp with a pEmitter node creating small white circle particles floating upward slowly on a dark navy background. Set the particle count low, add slight randomness to size and velocity, and make them fade out over their lifetime. Connect through pRender to MediaOut.
```

### 3D Text with Extrusion
```
Create a Fusion comp with a Text3D node reading "EPIC" in bold white. Add an extrusion depth of 0.2, light it with a single spotlight from the upper left, and place a dark gradient background behind it. Set up a Camera3D and a Merge3D connecting to a Renderer3D to MediaOut.
```

### Floating Dust Particles
```
Add a Fusion comp to the current clip that overlays subtle floating dust particles. Use a pEmitter with very small particles (size 0.002), low velocity with random drift, and long lifespan. Set particle color to warm white, blend over MediaIn1 at low opacity using Screen blend mode.
```

---

## Tips

- Fusion tool IDs use registered names: `TextPlus` (not `Text+`), `FilmGrain` (not `Film Grain`), `pEmitter` (not `ParticleEmitter`).
- You can chain prompts: first create the comp, then refine individual node settings in follow-up messages.
- If a prompt is too complex, break it into steps: create nodes first, then wire connections, then animate.
- Use "show me the node graph" or "list all nodes in the current Fusion comp" to inspect what exists before modifying.
- If nodes aren't rendering, check that the chain is fully connected to MediaOut1 -- this is the most common issue.
