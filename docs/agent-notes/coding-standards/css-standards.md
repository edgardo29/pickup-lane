# CSS Standards and Best Practices

## Purpose

This document defines general standards for writing, organizing, reviewing, and maintaining CSS.

Its purpose is to keep styles:

- predictable
- reusable
- accessible
- responsive
- maintainable
- safe to modify
- consistent across a codebase

These rules are intentionally project-agnostic. They do not define a particular visual design, framework, folder structure, or product architecture.

## Relationship to Project Rules

This document defines transferable CSS engineering practices. It does not replace the local rules of an adopting project.

Each project should separately define its own:

- stylesheet and folder structure
- naming convention
- supported browser baseline
- design tokens and visual language
- component ownership boundaries
- build, lint, formatting, and test commands
- framework-specific or platform-specific constraints
- exception and approval process

Project rules define implementation details and may strengthen this standard. When no project rule exists, use this document as the default engineering standard. A project rule that conflicts with a **MUST** or **MUST NOT** in this document requires an explicit, documented exception that identifies the reason and scope.

## Requirement Language

The following terms are intentional:

- **MUST** means the rule is required.
- **MUST NOT** means the practice is prohibited unless a documented exception exists.
- **SHOULD** means the rule is strongly preferred, but a justified exception may exist.
- **SHOULD NOT** means the practice should normally be avoided.
- **MAY** means the practice is optional.

---

# 1. Core Principles

CSS work SHOULD follow these principles:

1. **Keep ownership clear.** Styles should live as close as practical to the component, layout, or shared system they affect.
2. **Reuse before adding.** Existing variables, patterns, and shared styles must be checked before new ones are introduced.
3. **Keep the cascade understandable.** Prefer low-specificity selectors and predictable source order over override chains.
4. **Name by responsibility.** Class names should describe components, elements, variants, and states rather than visual accidents or temporary positions.
5. **Design for change.** Styles should tolerate different content lengths, viewport sizes, languages, zoom levels, and surrounding layouts.
6. **Treat accessibility as required behavior.** Focus visibility, contrast, text resizing, motion preferences, and target sizing are part of correct CSS.
7. **Avoid unnecessary global effects.** A local styling change should not alter unrelated parts of the interface.
8. **Prefer boring, readable CSS.** Cleverness is not a substitute for maintainability.

---

# 2. CSS Organization

## 2.1 Use Clear Style Categories

A codebase SHOULD distinguish between the following responsibilities:

- reset or normalization rules
- design tokens and custom properties
- document-level defaults
- layout primitives
- reusable components
- local component or screen styles
- state and utility classes
- third-party overrides

The exact file structure may differ, but responsibilities SHOULD remain clear.

## 2.2 Use the Narrowest Correct Scope

A rule SHOULD be placed in the narrowest stable scope that owns it.

Global CSS should be limited to concerns that are truly global, such as:

- box sizing
- default typography
- root-level tokens
- document background and text color
- consistent media defaults
- focus conventions
- shared normalization

Component-specific or screen-specific styles MUST NOT be added to global CSS merely because it is convenient.

## 2.3 Do Not Prematurely Share Styles

A style should normally become shared after a real second use demonstrates the same visual or behavioral responsibility.

Earlier sharing is reasonable when a canonical owner is clearly needed to prevent parallel implementations from drifting, or when the style defines an intentional system-level contract.

Before sharing a style, confirm that:

- the responsibility is stable and explainable
- the abstraction reduces duplication or prevents likely drift
- consumers need substantially the same behavior
- the shared API does not require excessive variants or configuration

Do not create speculative abstractions merely because a style might be reused someday.

## 2.4 Keep Related Rules Together

Rules for the same component or styling responsibility SHOULD remain close together.

A stylesheet SHOULD generally organize a component in this order:

1. root
2. internal layout
3. child elements
4. variants
5. states
6. responsive changes
7. user preference queries

Do not scatter the same component across unrelated files unless a deliberate layering system requires it.

## 2.5 Imports Must Be Intentional

Every stylesheet import MUST have a clear owner and purpose.

Do not:

- import an unrelated stylesheet merely to reuse one class
- rely on a stylesheet being loaded accidentally elsewhere
- create circular or order-dependent import chains
- load the same stylesheet from multiple unrelated entry points without understanding the result

---

# 3. Cascade Management

## 3.1 Prefer Predictable Source Order

Use source order intentionally. Base rules should come before variants and states.

```css
.notice {
  padding: var(--space-4);
}

.notice--warning {
  border-color: var(--color-warning-border);
}

.notice.is-dismissed {
  display: none;
}
```

Do not place broad rules after narrow rules when doing so creates accidental overrides.

## 3.2 Understand an Override Before Adding One

Before adding an override, determine why the earlier rule applies.

Prefer correcting:

- selector scope
- source order
- inheritance
- a custom property value
- component ownership
- an incorrect shared abstraction

Do not add a stronger selector merely because it is faster than understanding the cascade.

## 3.3 Cascade Layers

A project MAY use cascade layers to make precedence explicit.

Example:

```css
@layer reset, tokens, base, layout, components, utilities, overrides;
```

When a project adopts cascade layers:

- the layer order MUST be declared centrally
- participating stylesheets MUST follow the declared order
- new layers SHOULD NOT be introduced casually
- unlayered styles MUST be handled deliberately because they outrank normal layered declarations

Do not introduce cascade layers during an unrelated styling change without evaluating their project-wide effect.

---

# 4. Selectors and Specificity

## 4.1 Prefer Classes

Classes SHOULD be the primary styling hook.

```css
.dialog {}
.dialog__header {}
.dialog__actions {}
.dialog--compact {}
.dialog.is-open {}
```

Avoid using the following as primary styling hooks:

- IDs
- deeply nested element selectors
- DOM position
- text content
- generated class names from external systems
- inline styles added only to defeat the cascade

## 4.2 Keep Specificity Low

Selectors SHOULD normally remain within one or two class-level conditions.

Preferred:

```css
.toolbar__button {}
.toolbar__button:hover {}
.toolbar.is-disabled .toolbar__button {}
```

Avoid:

```css
main .content-area .toolbar .toolbar__group button.toolbar__button.primary {}
```

Do not:

- use IDs to increase specificity
- repeat classes to increase specificity
- chain unrelated ancestors
- mirror the full DOM structure in selectors

## 4.3 Use `:where()` for Zero-Specificity Grouping

Use `:where()` when structural context or selector grouping is useful but should not increase specificity.

```css
:where(.search-field, .filter-field) input {
  min-inline-size: 0;
}
```

Use `:is()` when the matched selector should contribute specificity.

## 4.4 Avoid Styling by Element Position

Avoid selectors such as:

```css
.list > div:nth-child(3) {}
.panel p:last-child {}
```

These selectors are acceptable only when position is the actual semantic rule, not a substitute for a missing class.

## 4.5 Avoid Broad Descendant Selectors

Broad selectors can unintentionally affect nested components.

Avoid:

```css
.card button {}
.content a {}
.sidebar div {}
```

Prefer a direct class owned by the component:

```css
.card__action {}
.content__link {}
.sidebar__section {}
```

## 4.6 `!important`

`!important` MUST NOT be used as a normal override strategy.

It MAY be used for a narrow, documented exception such as:

- an accessibility safeguard
- a deliberate override utility
- an uncontrollable third-party style
- an unavoidable inline style from an external library

Every non-obvious use MUST include a short explanation.

```css
/* Overrides an inline width generated by the vendor widget. */
.external-widget {
  inline-size: 100% !important;
}
```

---

# 5. Naming Conventions

## 5.1 Name by Responsibility

Class names should describe what an element is or does.

Prefer:

```css
.account-summary {}
.account-summary__total {}
.account-summary--empty {}
```

Avoid:

```css
.left-box {}
.blue-text {}
.margin-top-20 {}
.second-row {}
```

Names based on color, coordinates, or current placement become misleading when designs change.

## 5.2 Use a Consistent Component Pattern

A project SHOULD use one predictable naming convention.

A BEM-like convention is acceptable:

```css
.component {}
.component__element {}
.component--variant {}
.component.is-state {}
```

The exact convention may differ, but a codebase SHOULD NOT mix several incompatible naming systems without a documented reason.

## 5.3 Use Stable Prefixes

Locally scoped classes SHOULD use a stable component or domain prefix.

```css
.data-table {}
.data-table__header {}
.data-table__cell {}
```

Avoid introducing broad global names such as:

```css
.card {}
.header {}
.title {}
.active {}
.container {}
```

Broad names are acceptable only when they belong to an intentional shared primitive with a documented contract.

## 5.4 Separate Variants from States

Variants describe a supported visual form:

```css
.button--danger {}
.button--compact {}
```

States describe current behavior or condition:

```css
.button.is-loading {}
.button.is-disabled {}
```

Do not use state names for permanent variants or variant names for temporary states.

## 5.5 Prefer Native State Selectors When Available

Use native state selectors when they accurately represent the condition:

```css
button:disabled {}
input:invalid {}
details[open] {}
[aria-expanded="true"] {}
```

Do not duplicate native state into a class unless the component architecture requires it.

## 5.6 Data Attributes

Data attributes MAY be used for finite styling modes or states.

```html
<section class="results" data-density="compact">
```

```css
.results[data-density="compact"] {
  --result-gap: var(--space-2);
}
```

Do not encode arbitrary application data into class names or selectors.

---

# 6. Design Tokens and Custom Properties

## 6.1 Centralize Reusable Values

Repeated design values SHOULD be represented by custom properties.

Typical token categories include:

- colors
- spacing
- typography
- radii
- shadows
- borders
- control heights
- transitions
- z-index levels
- layout widths

```css
:root {
  --color-surface: #ffffff;
  --color-text: #1b1b1b;
  --space-1: 0.25rem;
  --space-2: 0.5rem;
  --space-4: 1rem;
  --radius-md: 0.5rem;
}
```

## 6.2 Prefer Semantic Tokens

Prefer tokens that communicate purpose:

```css
--color-text-muted
--color-border-danger
--color-surface-elevated
--color-action-primary
```

Avoid relying only on literal names:

```css
--gray-500
--red-600
--blue-dark
```

Primitive palette tokens MAY exist underneath semantic tokens, but components SHOULD consume semantic tokens whenever practical.

## 6.3 Use Local Custom Properties for Component Configuration

A component MAY define local custom properties to make internal relationships explicit.

```css
.panel {
  --panel-padding: var(--space-4);
  --panel-gap: var(--space-3);

  display: grid;
  gap: var(--panel-gap);
  padding: var(--panel-padding);
}

.panel--compact {
  --panel-padding: var(--space-2);
  --panel-gap: var(--space-2);
}
```

This is usually preferable to repeating a full declaration block for each variant.

## 6.4 Avoid Token Abuse

Do not create a custom property for every single declaration.

A custom property is useful when it:

- is reused
- represents a system value
- changes by theme, context, state, or variant
- documents a meaningful relationship
- simplifies coordinated changes

## 6.5 Provide Fallbacks When Needed

Use fallbacks when a variable may legitimately be absent:

```css
color: var(--component-text-color, currentColor);
```

Do not use fallbacks to hide missing required tokens.

---

# 7. Resets and Base Styles

## 7.1 Use Predictable Box Sizing

Use border-box sizing consistently.

```css
*,
*::before,
*::after {
  box-sizing: border-box;
}
```

## 7.2 Normalize Media Elements

Raster images, pictures, video, and canvas elements SHOULD not overflow their containers by default.

```css
img,
picture,
video,
canvas {
  display: block;
  max-inline-size: 100%;
}
```

Do not include `svg` in a blanket media reset. Inline SVG often serves as an icon or control graphic and may require its own sizing, display, and alignment contract.

Do not apply dimensions that distort intrinsic aspect ratios.

## 7.3 Preserve Useful Browser Defaults

A reset MUST NOT remove useful accessibility behavior without replacing it.

Do not globally remove:

- focus outlines
- list semantics
- form control usability
- link distinction
- text selection
- scrolling behavior

## 7.4 Inheritance

Typography and color SHOULD generally inherit from higher-level elements.

Form controls may need explicit inheritance:

```css
button,
input,
select,
textarea {
  font: inherit;
}
```

Do not force inheritance for properties whose inherited behavior would be surprising or unsafe.

---

# 8. Layout

## 8.1 Use the Right Layout System

Use Flexbox for primarily one-dimensional alignment and distribution.

Use Grid for two-dimensional layout, repeated tracks, and explicit row-column relationships.

Use normal document flow whenever it already solves the layout.

Do not use absolute positioning as the primary layout system for ordinary content.

## 8.2 Prefer `gap` for Layout Spacing

Use `gap` for spacing between children in flex and grid layouts.

```css
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
}
```

Do not create complex child-margin rules when `gap` expresses the relationship directly.

## 8.3 Avoid Fragile Fixed Dimensions

Do not use fixed widths or heights for content that may grow.

Avoid:

```css
.message {
  width: 420px;
  height: 120px;
}
```

Prefer:

```css
.message {
  inline-size: min(100%, 32rem);
  min-block-size: 7.5rem;
}
```

Use fixed dimensions only when the dimension is part of the component's actual contract.

## 8.4 Use `min-width: 0` in Flexible Layouts

Flex and grid children may refuse to shrink because of their intrinsic minimum size.

Use:

```css
.layout__main {
  min-inline-size: 0;
}
```

when content must be allowed to shrink or wrap inside a flexible track.

## 8.5 Logical Properties

Prefer logical properties when they improve adaptability to writing direction.

```css
margin-inline-start: auto;
padding-block: var(--space-3);
border-inline-start: 1px solid var(--color-border);
```

Physical properties remain acceptable when the physical direction is intentionally meaningful.

## 8.6 Containing Blocks and Positioning

When using `position: absolute`, the containing block SHOULD be intentional and locally understandable.

```css
.icon-button {
  position: relative;
}

.icon-button__badge {
  position: absolute;
  inset-block-start: 0;
  inset-inline-end: 0;
}
```

Do not depend accidentally on a distant positioned ancestor.

## 8.7 Sticky Positioning

Before using `position: sticky`, verify:

- the intended scroll container
- ancestor overflow rules
- the inset value
- stacking behavior
- behavior at narrow widths and high zoom

Do not add sticky positioning without testing actual scrolling behavior.

## 8.8 Overflow

Use overflow rules deliberately.

Do not apply `overflow: hidden` merely to conceal layout problems. It can clip:

- focus rings
- menus
- tooltips
- shadows
- translated content
- zoomed content

Prefer correcting the underlying layout first.

---

# 9. Units and Sizing

## 9.1 Relative Units

Use `rem` for values that should scale with root text size, including most typography and spacing.

Use `em` for values that should scale with the current element's font size.

Use percentages, fractional grid units, intrinsic sizing, and modern functions for fluid layouts.

Pixels remain acceptable for values such as:

- thin borders
- small visual offsets
- raster-related dimensions
- cases where device-independent scaling is not desired

## 9.2 Avoid Overusing Viewport Units

Viewport units can behave unexpectedly on mobile browsers and at different zoom levels.

Prefer modern dynamic viewport units when viewport sizing is genuinely required:

```css
min-block-size: 100dvh;
```

Do not force every screen to a viewport height when content should define its own height.

## 9.3 Use `min()`, `max()`, and `clamp()` Deliberately

Modern CSS functions can express bounded fluid sizing.

```css
inline-size: min(100%, 70rem);
padding-inline: max(var(--space-4), env(safe-area-inset-left));
```

Fluid typography with `clamp()` is an optional technique, not a default requirement. Use it only when the design intentionally calls for type to scale continuously between tested bounds and when it remains compatible with the project's typography system.

```css
.display-heading {
  font-size: clamp(1.75rem, 1.4rem + 1.5vw, 3rem);
}
```

Every bound should have a clear design reason. Do not use fluid formulas merely because they are concise.

## 9.4 Aspect Ratio

Use `aspect-ratio` when an element needs a stable proportion.

```css
.thumbnail {
  aspect-ratio: 16 / 9;
  object-fit: cover;
}
```

Do not combine fixed width, fixed height, and aspect ratio unless the interaction is intentional.

---

# 10. Responsive Design

## 10.1 Design for Reflow

Content MUST reflow without loss of information or functionality and without
requiring scrolling in two dimensions at a width equivalent to **320 CSS
pixels** for vertically scrolling content or a height equivalent to **256 CSS
pixels** for horizontally scrolling content.

Content that genuinely requires a two-dimensional layout for its usage or
meaning, such as a complex data table, diagram, map, or editing canvas, may be
treated as an exception.

The 320 CSS-pixel requirement is equivalent to viewing a 1280 CSS-pixel-wide
viewport at 400% zoom.

Responsive behavior should be driven by content needs rather than specific device models.

## 10.2 Mobile-First Rules

When practical, write the base rule for the narrowest layout and add complexity as space becomes available.

```css
.summary-grid {
  display: grid;
  gap: var(--space-4);
}

@media (min-width: 48rem) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
```

A desktop-first exception is acceptable when it clearly produces simpler and safer CSS.

## 10.3 Breakpoints

Breakpoints SHOULD be selected where the layout needs to change, not because a named device width is popular.

Prefer a small, shared breakpoint set when it fits the design.

A component-specific breakpoint is acceptable when its content has a real need.

## 10.4 Keep Responsive Rules Near Their Owner

Responsive changes SHOULD remain near the component or layout they affect.

Do not create a separate global mobile stylesheet containing unrelated rules from across the codebase.

## 10.5 Container Queries

Use container queries when a component's layout depends on the space allocated to the component rather than the viewport.

```css
.widget {
  container-type: inline-size;
}

@container (min-width: 32rem) {
  .widget__content {
    grid-template-columns: 1fr auto;
  }
}
```

Do not use container queries without defining and understanding the query container.

## 10.6 Avoid CSS and JavaScript Breakpoint Drift

Do not duplicate responsive presentation logic in JavaScript when CSS can handle it.

JavaScript may respond to viewport or container changes only when behavior, data loading, or rendering logic genuinely depends on the size.

When both CSS and JavaScript require the same breakpoint, the value SHOULD be centralized or clearly documented to prevent drift.

## 10.7 Zoom and Text Enlargement

Layouts affected by a change SHOULD be checked at increased browser zoom and with enlarged text when the risk warrants it.

Do not assume that a desktop viewport remains spacious after zooming.

---

# 11. Typography and Content Resilience

## 11.1 Use a Defined Type Scale

Typography SHOULD use a limited, reusable scale rather than unrelated values throughout the codebase.

```css
:root {
  --font-size-sm: 0.875rem;
  --font-size-md: 1rem;
  --font-size-lg: 1.25rem;
  --font-size-xl: 1.5rem;
}
```

## 11.2 Use Unitless Line Height

Use unitless line heights for ordinary text so line height scales with font size.

```css
body {
  line-height: 1.5;
}
```

Fixed line heights may be used for tightly controlled single-line controls or display text when carefully tested.

## 11.3 Do Not Depend on Exact Text Length

Components MUST tolerate the content states and variation included in their defined contract. Depending on the component, that contract may include:

- longer labels
- translated content
- user-generated content
- large numbers
- empty values
- validation messages
- multi-line text

Components SHOULD also anticipate reasonable additional variation beyond the minimum contract when doing so does not compromise the intended behavior.

Do not use fixed heights that assume a label will always remain on one line.

## 11.4 Truncation

Text truncation SHOULD be a deliberate product decision rather than an automatic response to layout pressure.

```css
.item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

When truncation hides meaningful information, provide a reliable way to access the complete value.

Do not use ellipsis merely to conceal a layout that should wrap.

## 11.5 Long Unbroken Content

Use safe wrapping for content such as URLs, identifiers, and long user-provided strings.

```css
.content-value {
  overflow-wrap: anywhere;
}
```

Do not apply aggressive word breaking globally.

## 11.6 Font Loading

Web fonts SHOULD use an appropriate `font-display` strategy.

Fallback fonts should be chosen to reduce layout shift and preserve readability.

Do not block the interface unnecessarily while waiting for a decorative font.

---

# 12. Color, Contrast, and Themes

## 12.1 Use Semantic Color Tokens

Components SHOULD consume semantic color variables rather than raw values.

```css
.alert {
  color: var(--color-text-danger);
  background: var(--color-surface-danger);
  border-color: var(--color-border-danger);
}
```

Do not scatter raw color values throughout local styles when a suitable token exists.

## 12.2 Do Not Communicate Meaning Through Color Alone

Errors, warnings, selected states, and success states MUST have a non-color indicator where meaning would otherwise be lost.

Possible indicators include:

- text
- an icon
- shape
- pattern
- border treatment
- position
- an accessible state attribute

## 12.3 Contrast

Unless an adopting project defines a stricter accessibility target, CSS MUST meet WCAG 2.2 Level AA contrast requirements:

- normal text and images of normal text: at least **4.5:1** against the adjacent background
- large text and images of large text: at least **3:1** against the adjacent background
- visual information needed to identify user interface components and their states: at least **3:1** against adjacent colors
- graphical objects required to understand the content: at least **3:1** against adjacent colors

For WCAG contrast purposes, large text is at least 18 point regular text or 14 point bold text. Contrast values are thresholds and should not be rounded up.

Not every decorative boundary must meet non-text contrast. Apply the requirement when the visual boundary, icon, or state is necessary to identify or understand the interface.

Do not assume a color pair is acceptable because it looks readable on one monitor. Measure it with an appropriate contrast tool.

## 12.4 Theme Support

Themes SHOULD override semantic tokens rather than duplicate full component styles.

```css
:root {
  --color-surface: #ffffff;
  --color-text: #181818;
}

[data-theme="dark"] {
  --color-surface: #171717;
  --color-text: #f5f5f5;
}
```

Do not create separate copies of every component solely to support a theme.

## 12.5 System Color Preferences

A project MAY respect system preferences such as:

```css
@media (prefers-color-scheme: dark) {}
@media (prefers-contrast: more) {}
@media (forced-colors: active) {}
```

Support SHOULD be tested rather than assumed when a project adopts one of these preference modes.

---

# 13. Interaction States

## 13.1 Define Complete State Sets

Interactive controls SHOULD account for relevant states:

- default
- hover
- focus
- focus-visible
- active or pressed
- disabled
- loading
- selected or expanded
- invalid

Do not design only the default and hover states.

## 13.2 Do Not Make Hover Essential

Hover styles may enhance an interface but MUST NOT be the only way to reveal essential information or actions.

Touch devices may not provide reliable hover behavior.

## 13.3 Preserve Visible Focus

Interactive elements MUST have a clearly visible keyboard focus indicator.

```css
.control:focus-visible {
  outline: 0.1875rem solid var(--color-focus-ring);
  outline-offset: 0.125rem;
}
```

Do not use `outline: none` unless an equal or stronger visible replacement is provided.

## 13.4 Focus Rings Must Not Be Clipped

Containers around interactive content SHOULD allow space for focus indicators.

Avoid clipping them with unnecessary overflow rules.

## 13.5 Disabled States

Disabled controls MUST remain identifiable and readable.

Do not rely on extremely low opacity that makes text or icons illegible.

CSS must not be the only mechanism preventing interaction. Native disabled behavior or application logic must enforce the state.

## 13.6 Cursor Usage

Use `cursor: pointer` for elements that behave like clickable controls when the platform convention supports it.

Do not use a pointer cursor on non-interactive decorative elements.

Do not use cursor styling as a substitute for correct semantic HTML.

---

# 14. Forms and Controls

## 14.1 Prefer Native Controls

Use native form controls whenever they satisfy the requirement.

Custom control styling MUST preserve:

- keyboard access
- focus visibility
- checked and selected states
- disabled states
- high-contrast behavior
- sufficient target size

## 14.2 Labels and Validation

CSS MUST support visible labels, descriptions, required indicators, errors, and success messages without relying on placeholder text.

Validation styling MUST not depend on color alone.

## 14.3 Control Sizing

Controls SHOULD use consistent heights, padding, typography, borders, and focus treatment.

Do not create a completely separate control appearance for every context.

## 14.4 Placeholders

Placeholder text is supplemental and MUST NOT replace a label.

Placeholder contrast should remain readable without competing with entered content.

## 14.5 Autofill

Form styles SHOULD be tested with browser autofill.

Do not apply autofill overrides that hide text, reduce contrast, or make saved values indistinguishable.

## 14.6 Textareas

Textareas SHOULD generally remain resizable in at least one direction unless resizing would break a tightly controlled interaction.

```css
textarea {
  resize: vertical;
}
```

## 14.7 Appearance Reset

Use `appearance: none` only when the native appearance is deliberately replaced and all necessary states remain clear.

---

# 15. Motion and Animation

## 15.1 Motion Must Have a Purpose

Animation should communicate:

- state change
- continuity
- hierarchy
- feedback
- spatial relationship

Do not add motion only because an element can be animated.

## 15.2 Prefer Transform and Opacity

For frequent or continuous animation, prefer `transform` and `opacity` when they produce the required result.

Avoid repeatedly animating layout-heavy properties such as:

- width
- height
- top
- left
- margin

This is a guideline, not an absolute rule. Correct visual behavior takes priority over forcing every animation onto the compositor.

## 15.3 Avoid `transition: all`

Declare the intended properties explicitly.

```css
.button {
  transition:
    background-color 150ms ease,
    border-color 150ms ease,
    transform 150ms ease;
}
```

Avoid:

```css
.button {
  transition: all 150ms ease;
}
```

## 15.4 Reduced Motion

Meaningful motion MUST respect `prefers-reduced-motion`.

```css
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto;
  }

  .animated-element {
    animation: none;
    transition: none;
  }
}
```

Reduced motion does not always require removing every transition. Preserve essential state feedback while reducing nonessential movement.

## 15.5 Avoid Infinite Decorative Animation

Infinite animation SHOULD be limited to cases such as loading indicators or necessary live status feedback.

Decorative infinite motion can distract users and consume resources.

## 15.6 `will-change`

Do not apply `will-change` broadly or permanently.

Use it only for a measured performance need and remove it when the change is no longer imminent.

---

# 16. Media, Icons, and Generated Content

## 16.1 Images

Images SHOULD preserve aspect ratio and use an appropriate fit mode.

```css
.avatar {
  aspect-ratio: 1;
  object-fit: cover;
}
```

## 16.2 Background Images

Use CSS background images for decorative imagery, not meaningful content that requires accessible alternative text.

## 16.3 Icons

Icons should use a consistent sizing and alignment strategy.

Decorative icons should not create redundant accessible content.

Do not depend on emoji rendering for critical interface icons when cross-platform consistency matters.

## 16.4 Generated Content

Pseudo-element content SHOULD be decorative or supplemental.

Do not place essential instructions, labels, or status information only in `::before` or `::after`.

---

# 17. Stacking Context and Z-Index

## 17.1 Use a Defined Scale

A project SHOULD define a small z-index scale for shared layers.

```css
:root {
  --z-base: 0;
  --z-sticky: 100;
  --z-dropdown: 200;
  --z-overlay: 300;
  --z-modal: 400;
  --z-toast: 500;
}
```

Do not solve stacking problems with arbitrary values such as `999999`.

## 17.2 Understand Stacking Contexts

Properties that can create stacking contexts include:

- positioned elements with z-index
- transforms
- opacity below 1
- filters
- isolation
- certain containment values

Increasing `z-index` cannot escape an ancestor stacking context.

Before changing a z-index value, identify the relevant stacking contexts.

## 17.3 Overlays

Shared overlays SHOULD use a consistent layer system.

Do not rely on unrelated local z-index values to compete with dialogs, popovers, menus, or notifications.

---

# 18. Accessibility Requirements

CSS changes MUST preserve or improve accessibility.

At minimum, review:

- visible keyboard focus
- text and non-text contrast
- content at increased zoom
- text spacing
- narrow viewport reflow
- touch target size
- reduced motion
- forced-colors behavior when relevant
- meaningful states that do not rely only on color

## 18.1 Target Size

Pointer targets MUST meet WCAG 2.2 Level AA Target Size (Minimum): at least **24 by 24 CSS pixels**, unless a defined WCAG exception applies.

The recognized exceptions include:

- sufficient spacing around an undersized target
- an equivalent control on the same page that meets the requirement
- inline targets within text or targets constrained by surrounding line height
- controls whose size is determined by the user agent and not modified by the author
- presentations where the smaller target is essential or legally required

Larger targets are generally easier to use. Projects MAY adopt a larger preferred control size, and important or frequently used controls SHOULD consider the WCAG enhanced target of **44 by 44 CSS pixels** where practical.

When the visible control must remain small, an expanded hit area may be used as long as it does not overlap or interfere with nearby targets.

## 18.2 Visually Hidden Content

Use a tested visually hidden utility for accessible text that should not be visually displayed.

```css
.visually-hidden {
  position: absolute;
  inline-size: 1px;
  block-size: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
  border: 0;
}
```

Do not use `display: none` or `visibility: hidden` for content that must remain available to assistive technologies.

## 18.3 Forced Colors

Custom controls, icons, and focus indicators SHOULD be tested in forced-colors mode when supported by the target platforms.

Do not disable forced-color adjustment broadly without a specific need.

---

# 19. Performance

## 19.1 Avoid Excessive Selector Work

Modern browsers handle ordinary class selectors efficiently. Performance rules should not lead to unreadable CSS.

Still avoid:

- unnecessarily deep selectors
- universal selectors scoped across very large subtrees without reason
- expensive relational selectors applied too broadly
- repeated duplicate rules

## 19.2 Avoid Excessive Paint Cost

Use large blurs, filters, backdrop filters, fixed backgrounds, and complex shadows carefully.

Do not apply expensive effects across large scrolling areas without testing performance.

## 19.3 Avoid Layout Thrashing Through CSS-JavaScript Interaction

CSS and JavaScript should not repeatedly force synchronous layout by alternating style writes and layout reads.

When JavaScript controls styles, prefer toggling classes, attributes, or custom properties over writing many individual inline declarations.

## 19.4 Remove Dead CSS Carefully

Unused CSS SHOULD be removed, but only after confirming that selectors are not created dynamically or used outside the searched code path.

When a project adopts automated unused-CSS tooling, it MUST be configured for dynamic classes, generated selectors, and templates.

## 19.5 Keep Bundles Intentional

Do not load large style bundles on screens that do not need them when the build system supports safe code splitting.

Do not fragment CSS so aggressively that ordering and reuse become harder to understand.

---

# 20. Modern CSS and Browser Support

## 20.1 Follow the Supported Browser Baseline

New CSS features SHOULD be evaluated against the adopting project's browser support policy.

Do not avoid modern CSS solely because an obsolete browser lacks support.

Do not use a new feature without checking whether the supported browsers implement it adequately.

## 20.2 Progressive Enhancement

Use feature queries when a fallback is needed.

```css
.layout {
  display: flex;
}

@supports (display: grid) {
  .layout {
    display: grid;
  }
}
```

The base experience should remain usable when an optional enhancement is unavailable.

## 20.3 Vendor Prefixes

Vendor prefixes SHOULD be added through the project's build tooling when available.

Do not hand-maintain large prefixed declaration sets unless tooling cannot handle the case.

## 20.4 Experimental Features

Experimental or partially supported features require:

- a clear benefit
- verified browser support
- an acceptable fallback
- focused testing
- documentation when the choice is non-obvious

---

# 21. Utilities

## 21.1 Utilities Must Be Deliberate

Utility classes MAY be used for stable, reusable single-purpose behavior.

Examples:

```css
.u-visually-hidden {}
.u-text-center {}
.u-no-wrap {}
```

A utility system SHOULD have a clear scope and naming convention.

## 21.2 Avoid Ad Hoc Utility Proliferation

Do not create a new global utility every time one declaration is needed locally.

Avoid uncontrolled classes such as:

```css
.mt-17 {}
.width-413 {}
.blue-2 {}
```

## 21.3 Utilities and Components

Utilities may adjust a component from the outside, but they should not replace the component's internal styling contract.

A component should remain understandable without reconstructing its design from a long list of unrelated utility classes unless the project intentionally uses a utility-first methodology.

---

# 22. Third-Party Styles

## 22.1 Isolate Overrides

Third-party overrides SHOULD be scoped as narrowly as possible.

```css
.date-picker-wrapper .external-calendar__day {}
```

Place third-party overrides in a clearly identified location.

## 22.2 Do Not Depend on Unstable Internals

Avoid targeting generated or undocumented internal selectors from a third-party package.

Prefer:

- documented theming APIs
- CSS custom properties exposed by the package
- supported class hooks
- wrapper-level configuration

## 22.3 Document Fragile Overrides

An override tied to a specific third-party implementation SHOULD include a comment naming the dependency and reason.

---

# 23. Comments and Documentation

## 23.1 Explain Why, Not What

Comments should explain non-obvious decisions, constraints, or workarounds.

Useful:

```css
/* Keeps the focus ring visible outside the clipped scrolling region. */
```

Not useful:

```css
/* Add padding */
padding: 1rem;
```

## 23.2 Document Exceptions

Document exceptions involving:

- `!important`
- unusual specificity
- browser workarounds
- fragile third-party overrides
- non-obvious fixed dimensions
- intentional overflow clipping
- experimental features

## 23.3 Remove Stale Comments

Comments SHOULD be updated or removed when the related behavior changes.

Do not preserve commented-out CSS as a long-term backup system. Version control already serves that purpose.

---

# 24. Modifying Existing CSS

## 24.1 Inspect Before Editing

Before changing a style, determine:

- where the current rule is defined
- which selectors override it
- whether variables influence it
- whether the element has variants or states
- where the class is used
- whether responsive or preference rules change it
- whether a shared component owns the behavior

Do not patch the first matching declaration without understanding the full rule chain.

## 24.2 Fix the Correct Layer

When a style is wrong everywhere, fix the shared rule.

When it is wrong only in one context, add the narrowest justified contextual rule or introduce a supported variant.

Do not weaken a shared component globally to solve one local exception.

## 24.3 Avoid Specificity Escalation

A sequence like this indicates a structural problem:

```css
.table__header {}
.container .table__header {}
.page .container .table__header {}
```

Refactor ownership, variants, or source order instead of continuing the escalation.

## 24.4 Preserve Existing Contracts

Before renaming or removing a class, search for:

- markup usage
- JavaScript selectors
- automated tests
- analytics hooks
- third-party integrations
- documentation

A class may serve a behavioral purpose in addition to styling.

When practical, use dedicated data attributes for JavaScript hooks so styling classes can evolve independently.

## 24.5 Avoid Unrelated Cleanup

A focused CSS change SHOULD NOT include broad unrelated formatting or redesign work.

Separate cleanup from behavioral changes when doing so makes review and regression detection easier.

## 24.6 Refactor in Safe Steps

For a broad CSS refactor:

1. document current behavior
2. identify owners and dependencies
3. add or migrate to the new pattern
4. verify visual and interactive states
5. remove obsolete rules
6. run regression checks

Do not combine a large styling migration with unrelated product behavior changes unless necessary.

---

# 25. Tooling and Enforcement

A project SHOULD automate enforceable CSS standards when the value justifies the maintenance cost.

Possible tooling includes:

- formatting through Prettier or an equivalent formatter
- linting through Stylelint
- browser support checks through Browserslist-based tooling
- automatic prefixing
- duplicate selector detection
- invalid property detection
- design token validation
- visual regression testing
- accessibility testing

These tools are recommendations, not assumed infrastructure. Requirements involving a formatter, linter, browser matrix, visual regression system, or accessibility test runner apply only when the adopting project has selected and configured that tooling.

When a tool is adopted as a required project check:

- its shared configuration MUST be committed to the repository
- the canonical command SHOULD work without personal editor settings or shell aliases
- local and continuous-integration behavior SHOULD remain consistent
- failures and suppressions SHOULD be understandable to contributors

Personal editor settings or shell aliases MUST NOT be the only way to validate CSS.

## 25.1 Formatting

Use an automated formatter when the project adopts one.

Do not spend review time debating formatting that tooling already enforces consistently.

## 25.2 Lint Suppressions

When linting is adopted, suppressions SHOULD be narrow and documented.

Avoid disabling a rule for an entire stylesheet when a single-line exception is sufficient.

## 25.3 Visual Regression Testing

Visual regression testing MAY be adopted for stable, high-value, or regression-prone surfaces.

It should not be required for every CSS edit and does not replace interaction, accessibility, or responsive verification.

---

# 26. Verifying CSS Changes

Verification MUST be proportional to the risk and affected surface of the change. Do not claim or require checks that the project cannot actually run.

Choose the smallest verification scope that provides reasonable confidence, then expand it when shared ownership, accessibility, layout complexity, or browser-sensitive behavior increases the risk.

## 26.1 Low-Risk Changes

Examples include a local spacing, color-token, or border adjustment with no layout or interaction effect.

Typically verify:

- the directly affected component or screen
- the states visibly touched by the change
- the project's available formatter or linter, when adopted

## 26.2 Medium-Risk Changes

Examples include wrapping, responsive layout, form-control styling, overflow, sticky positioning, or a shared component variant.

Typically verify:

- relevant content and interaction states
- representative narrow and wide layouts
- keyboard focus when interactive content is involved
- increased zoom or enlarged text when layout resilience may be affected
- nearby consumers of a shared style

## 26.3 High-Risk Changes

Examples include global styles, shared tokens, resets, cascade order, typography foundations, overlays, navigation, broad refactors, or new browser-dependent features.

Typically verify:

- representative consumers across the affected scope
- keyboard, pointer, and touch behavior where relevant
- narrow, intermediate, and wide layouts
- long, translated, empty, loading, error, and disabled states as applicable
- reduced motion, forced colors, themes, or contrast preferences when affected
- more than one supported browser engine when behavior is browser-sensitive
- automated accessibility or visual regression checks when the project has adopted them and they cover the change

## 26.4 State Selection

Possible states include:

- empty
- loading
- populated
- error
- disabled
- selected
- expanded
- focused
- hovered
- long content
- missing optional content

Only test states the change can reasonably affect, but do not omit a relevant state merely because it is inconvenient to reproduce.

## 26.5 Browser Coverage

Multi-browser verification SHOULD be based on the project's supported browser baseline and the risk of the CSS feature involved. It is particularly valuable for forms, sticky positioning, overflow, viewport units, newer CSS features, and complex layout behavior.

---

# 27. Prohibited Patterns

The following patterns MUST NOT be introduced without a documented exception:

- page-specific or component-specific rules in global base styles
- IDs used to increase styling specificity
- repeated class selectors used to increase specificity
- uncontrolled `!important`
- deep selectors that mirror the DOM tree
- broad feature classes such as `.title`, `.header`, or `.active`
- inline styles used only to bypass CSS ownership
- `transition: all`
- removal of focus indicators without an equivalent replacement
- color-only communication of important state
- fixed heights for content that can grow
- arbitrary z-index escalation
- unnecessary `overflow: hidden`
- meaningful text placed only in pseudo-elements
- placeholder text used as a label
- hover-only access to essential information
- duplicate component systems for minor visual differences
- raw design values repeatedly added when a semantic token exists
- global utilities created for one local use
- viewport-specific JavaScript used only for presentation CSS can handle
- permanent broad use of `will-change`
- unrelated visual cleanup bundled into a focused CSS change

---

# 28. CSS Change Checklist

Before completing a CSS change, apply the checklist items that are relevant to the change. Mark an item as **N/A** when it does not apply rather than performing unnecessary work solely to satisfy the checklist:

## Ownership

- [ ] The rule is placed in the narrowest correct scope.
- [ ] Global CSS contains only genuinely global concerns.
- [ ] I checked for an existing shared pattern before adding a new one.
- [ ] Imports are explicit and intentional.

## Cascade and Selectors

- [ ] Selector specificity is low and understandable.
- [ ] I did not use an ID or repeat a class to increase specificity.
- [ ] I understand why any overridden rule applies.
- [ ] Any `!important` use is necessary, narrow, and documented.

## Naming

- [ ] Class names describe responsibilities rather than color, position, or spacing.
- [ ] Components, elements, variants, and states follow the project's convention.
- [ ] Broad generic class names are used only for documented shared primitives.

## Tokens and Values

- [ ] Existing design tokens are reused where appropriate.
- [ ] New tokens have a real reusable or semantic purpose.
- [ ] Raw colors and repeated arbitrary values were not introduced unnecessarily.

## Layout and Responsiveness

- [ ] Content can grow, wrap, or translate without breaking the layout.
- [ ] The layout reflows at narrow widths.
- [ ] Fixed dimensions are justified.
- [ ] Flex and grid children can shrink where required.
- [ ] Overflow rules do not conceal a deeper layout problem.
- [ ] Increased zoom and enlarged text were checked when layout or typography could be affected.

## Accessibility

- [ ] Keyboard focus remains clearly visible.
- [ ] Important meaning is not communicated through color alone.
- [ ] Text and required non-text contrast meet the defined WCAG thresholds.
- [ ] Pointer targets meet the 24 by 24 CSS-pixel minimum or a documented WCAG exception applies.
- [ ] Controls remain usable and identifiable in every relevant state.
- [ ] Motion respects reduced-motion preferences when relevant.
- [ ] Focus rings and interactive content are not clipped.

## Performance and Compatibility

- [ ] Expensive effects are limited and tested.
- [ ] New CSS features match the supported browser baseline.
- [ ] A fallback exists where required.
- [ ] No unnecessary JavaScript was added for presentation behavior CSS can handle.

## Verification

- [ ] Verification depth matches the risk and affected surface.
- [ ] Relevant component and interaction states were checked.
- [ ] Representative viewport sizes were checked when layout could be affected.
- [ ] Browser-specific behavior was checked where risk exists.
- [ ] Adopted linting, formatting, and automated checks pass when they apply.
- [ ] Unrelated screens and shared components were not unintentionally changed.


---

# 29. Normative Accessibility References

The measurable accessibility requirements in this document are based on WCAG 2.2:

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/)
- [Understanding Success Criterion 1.4.3: Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum)
- [Understanding Success Criterion 1.4.11: Non-text Contrast](https://www.w3.org/WAI/WCAG22/understanding/non-text-contrast.html)
- [Understanding Success Criterion 1.4.10: Reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow)
- [Understanding Success Criterion 2.5.8: Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum)

Projects may adopt stricter accessibility requirements. A decision to fall below these Level AA minimums is an explicit exception to this standard and MUST be documented, scoped, and approved through the adopting project's exception process.

---

# 30. Decision Rule

When several CSS solutions are possible, prefer the one that:

1. has the narrowest correct ownership
2. uses the lowest practical specificity
3. preserves native browser behavior
4. reuses existing semantic tokens and patterns
5. adapts to content and container size
6. remains accessible under keyboard use, zoom, contrast changes, and motion preferences
7. requires the least hidden knowledge to maintain
8. creates the smallest safe change

The best CSS solution is not the one with the fewest characters. It is the one whose behavior and ownership remain clear when the codebase changes.
