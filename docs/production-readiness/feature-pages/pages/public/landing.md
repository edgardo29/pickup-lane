# F01 — Landing

## 1. Existing Route(s)

- `/`

## 2. Purpose

Landing introduces Pickup Lane's ways to play and directs visitors into game discovery, account creation, or hosting. Signed-in players get a shorter route into Browse Games and Create Game.

## 3. Main Functionality

### 3.1. Start Playing

- Signed-out visitors can open Browse Games, Create Account, or Sign In from the hero and account card.
- Signed-in players see a welcome message and actions for Browse Games and Create Game in place of the account card.
- The shared navigation and footer provide access to other public destinations.

### 3.2. Learn How Pickup Lane Works

- The page presents the steps from finding games by day through joining and game-day coordination. The discovery step describes choosing a day to browse upcoming games; it does not claim that [Browse Games](browse-games.md) offers venue, format, skill-level, price, or open-spots filters.
- It introduces official games, community hosting, and Need a Sub, followed by host tools and expandable frequently asked questions.
- The How it Works navigation link lands at that section of this page.

## 4. Important Behavior & Decisions

### 4.1. Entry-Point Boundaries

Landing describes the available paths; it does not list games, create an account, reserve a spot, or publish a post. Those actions belong to [Browse Games](browse-games.md), [Create Account](../authentication/create-account.md), [Create Game](../hosting/create-game.md), and [Need a Sub](need-a-sub.md).

### 4.2. Account State

Guest actions appear when no app account is available. While account state is loading, the page can show the public entry points after a short delay so visitors have a way forward.

## 5. Tests & Edge Cases

These scenarios are for future verification; none are marked complete.

### 5.1. Established Behavior

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 1 | ☐ | Open Landing while signed out. | Browse Games, Create Account, and Sign In are available; the page introduces the three ways to play and the host tools. |
| 2 | ☐ | Open Landing with a complete signed-in account. | A welcome message and Browse Games/Create Game actions appear; the guest account card is absent. |
| 3 | ☐ | Select How it Works from navigation. | The page moves to its How it Works section without leaving Landing. |
| 4 | ☐ | Expand and collapse each FAQ item. | The corresponding answer becomes visible and can be hidden again. |
| 5 | ☐ | Follow the hero or account actions. | Each action opens its named destination without performing that destination's workflow on Landing. |

### 5.2. Boundary and Recovery Cases

| # | Done | Scenario | Expected result |
|---:|:---:|---|---|
| 6 | ☐ | Account state takes time to resolve. | Public entry actions become available after the short fallback delay; a signed-in result replaces them with signed-in actions when it arrives. |
| 7 | ☐ | A signed-in account has no first name. | The welcome line remains readable without an empty or broken name. |
| 8 | ☐ | Read the How it Works discovery step. | It describes choosing a day to browse upcoming games and does not claim that Browse offers venue, format, skill-level, price, or open-spots filters. |

## 6. Open Items to Resolve

**None**.
