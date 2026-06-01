---
name: Luminous Protocol
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#b9cacb'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#849495'
  outline-variant: '#3a494b'
  surface-tint: '#00dbe7'
  primary: '#e1fdff'
  on-primary: '#00363a'
  primary-container: '#00f2ff'
  on-primary-container: '#006a71'
  inverse-primary: '#00696f'
  secondary: '#ecb2ff'
  on-secondary: '#520071'
  secondary-container: '#cf5cff'
  on-secondary-container: '#480063'
  tertiary: '#f8f6ff'
  on-tertiary: '#2b3040'
  tertiary-container: '#d6daf0'
  on-tertiary-container: '#5a5f71'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#74f5ff'
  primary-fixed-dim: '#00dbe7'
  on-primary-fixed: '#002022'
  on-primary-fixed-variant: '#004f54'
  secondary-fixed: '#f8d8ff'
  secondary-fixed-dim: '#ecb2ff'
  on-secondary-fixed: '#320047'
  on-secondary-fixed-variant: '#74009f'
  tertiary-fixed: '#dee1f7'
  tertiary-fixed-dim: '#c2c6db'
  on-tertiary-fixed: '#161b2b'
  on-tertiary-fixed-variant: '#414658'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  body-base:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: 0em
  code-label:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.05em
  code-data:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin-desktop: 40px
  margin-mobile: 16px
  container-max-width: 1440px
---

## Brand & Style

The design system is engineered for a premium, high-stakes AI automation environment. It targets high-growth enterprises and developer-centric agencies who require a sense of absolute precision and futuristic capability. The brand personality is "The Ghost in the Machine"—highly intelligent, invisible yet omnipresent, and undeniably powerful.

The style is a sophisticated evolution of **Cyberpunk Minimalism**. It rejects the cluttered "junk-tech" trope in favor of a **Glassmorphic** and **Luminous** aesthetic. The UI relies on rich, deep blacks to create infinite depth, while UI elements appear as floating glass panes with radioactive-inspired light paths. The emotional response is one of calm, focused control amidst complex data streams.

## Colors

The palette is rooted in the "Deep Dark" spectrum to maximize the contrast of the glowing accents.
- **Primary (#00F2FF):** "Neon Teal." Used for active states, primary actions, and successful AI execution pulses.
- **Secondary (#BD00FF):** "Electric Purple." Used for creative automation paths, secondary highlights, and luxury "Premium" indicators.
- **Background (#050505):** A rich, absolute black that provides the canvas for depth and luminosity.
- **Surface (#0A0F1E):** "Midnight Blue." Used for container backgrounds to provide a subtle lift from the absolute black.

Color application should follow a "Light Emitting" principle: borders should often use 1px gradients that transition from the primary color to transparent, mimicking a laser-cut edge.

## Typography

This design system utilizes a dual-font strategy to balance human-centric UI with technical AI data.
- **Inter** handles all structural UI elements, headlines, and body copy. It is clean, modern, and provides the "Premium SaaS" feel.
- **JetBrains Mono** is reserved for metadata, terminal outputs, AI confidence scores, and status labels. This creates an immediate "developer-grade" association.

Headlines should use tight letter-spacing for a high-end editorial look. Data labels in JetBrains Mono should be all-caps with increased letter-spacing to enhance legibility in dense dashboard views.

## Layout & Spacing

The layout follows a **Fixed Grid** model for desktop to maintain the integrity of complex data visualizations, while transitioning to a **Fluid** model for mobile devices. 

- **Desktop:** 12-column grid with 24px gutters. Content is housed in "Modules" that snap to the grid.
- **Tablet:** 8-column grid with 16px gutters.
- **Mobile:** 4-column grid with 16px margins.

Spacing should be generous between modules (32px+) to prevent the dark interface from feeling cramped. Internal module padding should be consistent at 24px to create a cohesive internal rhythm.

## Elevation & Depth

Depth is not achieved through traditional shadows, but through **Tonal Layering** and **Luminosity**.

1.  **Base:** The `#050505` floor.
2.  **Mid-Ground:** Surfaces use a semi-transparent Midnight Blue (`#0A0F1E` at 60% opacity) with a `20px` backdrop blur (Glassmorphism).
3.  **Highlights:** 1px inner borders (strokes) using the Primary or Secondary color at 20% opacity. This creates a "light-catching" edge.
4.  **Glows:** For high-priority elements, use a `0px 0px 15px` outer glow (drop shadow with 0 spread) using the primary color at low opacity (15-20%). This simulates a neon tube effect.

## Shapes

The design system uses a "Soft Tech" approach. Elements are not fully sharp (which feels aggressive) nor fully rounded (which feels too consumer-grade). 

- **Standard Elements:** 4px (0.25rem) radius for buttons, input fields, and small cards.
- **Primary Containers:** 8px (0.5rem) radius for main dashboard modules.
- **Interactive States:** On hover, a border-radius "pulse" can be simulated by increasing the glow, but the physical radius remains static.

## Components

- **Buttons:** Primary buttons use a solid Teal-to-Purple gradient or solid Teal with black text. Secondary buttons are "Ghost" style with a 1px Teal border and a very subtle Teal glow on hover.
- **Input Fields:** Dark background (#050505) with a 1px border. On focus, the border glows Teal and the label (in JetBrains Mono) shifts to Teal.
- **Cards/Modules:** Utilize the Glassmorphic stack (Backdrop blur + semi-transparent background). Headers within cards should have a subtle bottom separator line (1px, 10% white).
- **Status Indicators:** Use small glowing pips. An "Active" AI agent should have a pulsing Teal dot with a soft radial blur behind it.
- **Data Tables:** Row lines should be extremely faint (5% white). The "Header" row should use JetBrains Mono in all-caps.
- **AI Pulse:** A specialized component—a horizontal line that carries a "light packet" (a small gradient segment) moving across the screen to indicate background processing.