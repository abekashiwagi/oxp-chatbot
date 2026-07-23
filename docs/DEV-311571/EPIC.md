# DEV-311571: ELI+ Chatbot Widget — New UI Design

## Epic Description

### What We're Building

A redesigned chatbot widget for prospect-facing property websites. The widget (branded "ELI+") gives prospective renters a way to ask questions, get answers about the property, and book tours — all from a floating chat interface on the property website.

### Design Overview

**Launcher Button:**
- Pill-shaped button fixed to the bottom-right of the page
- Dark blue background with white text "Chat with us" and a white chat bubble icon
- When the chat is open, the button collapses to a circular close button

**Chat Panel (opens on click):**
- 400×600px floating panel with rounded corners and a light gray background (#f7f8fa)
- Three sections stacked vertically:
  1. **Welcome Header** — "Welcome, I'm ELI" title + legal disclaimer with links to Terms and Privacy Policy
  2. **Conversation Area** — Scrollable message thread. Bot messages appear as white bubbles on the left. User messages appear as blue bubbles on the right.
  3. **Composer** — Rounded input field with "Type your message" placeholder and a circular blue send button

**Initial Greeting:**
When the panel opens, ELI+ immediately shows a message: "Hi I'm ELI+, a virtual leasing agent for The Residences community. I can help with tours, pricing, availability, amenities and the application process. Would you like to book a tour?"

**Footer:**
"Powered by Entrata" branding at the bottom of the panel.

### Behavior

- User types a message and presses Enter or clicks the send button
- Their message appears as a blue bubble aligned right
- A typing indicator (three dots) shows while waiting for a response
- The bot's reply appears as a white bubble aligned left
- Conversation scrolls automatically as new messages appear
- The panel closes when the user clicks the FAB button again or presses Escape
- On mobile (<640px), the panel goes full-screen

### Links

- **Terms link** opens: https://legal.entrata.com/prospect-portal-resident-portal-terms
- **Privacy Policy link** opens: https://www.entrata.com/privacy-policy

---

## Feature Essentials

### Before

Prospect-facing property websites have no embedded AI chat experience. If a prospect visits the site after hours or doesn't want to call, they have no way to get immediate answers about availability, pricing, tours, or the application process. They either leave the site or fill out a static contact form and wait for a callback.

### After

- A "Chat with us" button appears on every property website page
- Clicking it opens a chat panel with a greeting from ELI+, the virtual leasing agent
- Prospects can ask questions about tours, pricing, availability, amenities, and applications
- ELI+ responds conversationally in real-time
- The experience includes a legal disclaimer with links to Terms and Privacy Policy
- "Powered by Entrata" branding is shown at the bottom
- Works on desktop and mobile (full-screen on small screens)

### NOT Included

- No live agent handoff in this release
- No proactive chat (the widget doesn't pop open automatically)
- No file/image sharing
- No appointment booking directly inside the chat (ELI+ can direct them, but doesn't embed a calendar picker)
- No multi-language support
- No chat history persistence across sessions (conversation resets on page reload)

### Who

- **Prospective Renters** — Get instant answers about the property without waiting for business hours or a callback
- **Leasing Teams** — Reduce inbound call/email volume for common questions (hours, pricing, availability)
- **Property Managers** — Capture more leads from website traffic by engaging visitors who would otherwise bounce

### Why

Prospect websites get traffic 24/7 but leasing offices are only staffed during business hours. Prospects who visit after hours and can't get answers bounce without converting. An always-on AI chat widget captures those visitors, answers their questions immediately, and drives them toward booking a tour — increasing lead conversion from existing website traffic.

### New Permissions

No new permissions required. The widget is embedded on the public-facing property website and is available to all visitors.

### Settings

- Property-level feature flag controls whether the widget appears on a given property's website
- The greeting message and property name are configurable per property

### FAQs

**Q: Can prospects use this on mobile?**
A: Yes. On screens smaller than 640px, the chat panel goes full-screen for a native-feeling experience.

**Q: What happens if the AI backend is unavailable?**
A: The widget shows a system message: "Sorry, I had trouble reaching the leasing system. Please try again."

**Q: Does the chat persist if they navigate to another page?**
A: No. The conversation resets on page navigation. Session-based persistence within the same page load only.

**Q: Is there branding customization?**
A: The widget uses Entrata's default branding. Property-specific color theming is not in this release.

**Q: Where does the Terms link go?**
A: https://legal.entrata.com/prospect-portal-resident-portal-terms

### Adoption Method Details

Controlled by a property-level feature flag. When enabled, the widget script is injected into the property's website. Default: OFF. Entrata enables it per property upon request.
