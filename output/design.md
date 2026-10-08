# Campus Customs Design

## Visual changes implemented

Problem 10 introduces a premium Yale-inspired storefront treatment while preserving the existing routes and database-backed behavior. The homepage now has a real catalogue-image hero, editorial introduction, featured catalogue products, a promotional collection band, and a branded footer. Product cards and product detail pages use consistent image areas, rounded surfaces, shadows, hover zoom, stock indicators, and clearer hierarchy. The navigation and floating chatbot were also restyled as part of the same visual system.

## Colors, typography, and direction

The palette uses Yale-inspired deep navy (`#00356B`), deeper navy backgrounds, warm ivory, white, soft neutrals, and restrained gold accents. DM Sans provides contemporary navigation, labels, and body copy; Playfair Display supplies the editorial italic accents and collegiate character. Spacious layouts, subtle geometric rings, restrained shadows, and small motion details create a polished lifestyle-store feel.

## Engagement and product discovery

The hero makes the collection immediately discoverable with a prominent Shop the collection action and real product photography. Featured catalogue items, consistent cards, readable prices, category labels, hover feedback, and enlarged product views help shoppers compare items and purchase with more confidence. The chatbot launcher and its dynamically returned product cards use the same navy, ivory, gold, and card styling as the rest of the store.

## Responsive and accessible behavior

Responsive breakpoints reflow the hero, featured products, product grid, details, footer, navigation, forms, and chat panel for tablet and mobile widths. Focus-visible outlines are provided for keyboard users, contrast is maintained across the navy/ivory surfaces, controls retain labels, and `prefers-reduced-motion: reduce` disables nonessential animation and smooth scrolling. Existing authentication, chat, search, dynamic product-card, and database-backed product behavior remains in place.

## Verification

- `npm run build` passed after the redesign.
- The implementation uses catalogue image URLs already returned by the API; no database changes were made for styling.
- Source-level checks confirm the existing routes, chat widget, authentication forms, product cards, and product detail links remain present. Full browser visual verification requires running the local backend and frontend in a browser.
