# F15 — Browse Games Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/player-facing/F15-browse-games-spec.md`  
**Endpoints:** `GET /games/browse`

## 1. Page requirements

| # | Spec section | Requirement                                                    | In the code? | What's missing |
|---|--------------|----------------------------------------------------------------|--------------|----------------|
| R1 | 3.1          | 14 dates in two sets of seven                                  | Yes          | —              |
| R2 | 3.1          | Arrows switch sets, not the selected date                      | Yes          | —              |
| R3 | 3.1          | Strip shows the set containing the selected date               | Yes          | —              |
| R4 | 3.1          | Opens on today; date kept in the link                          | Yes          | —              |
| R5 | 3.2          | Grouped by start hour with hour totals                         | Yes          | —              |
| R6 | 3.2          | Official and community games in one list                       | Yes          | —              |
| R7 | 3.2          | Batches of 40 with Load More                                   | Yes          | —              |
| R8 | 3.3          | Card contents                                                  | Yes          | —              |
| R9 | 3.4          | Card opens Game Details                                        | Yes          | —              |
| R10 | 4.1          | Which games appear                                             | Yes          | —              |
| R11 | 4.2          | Registration cutoff 5 minutes after start                      | Yes          | —              |
| R12 | 4.3          | Full games stay listed, no waitlist badge                      | Yes          | —              |
| R13 | 4.4          | Spot counts, including unexpired holds                         | Yes          | —              |
| R14 | 4.5          | Market timezone for dates, times and hour groups               | Yes          | —              |
| R15 | 4.5          | Window moves when the market day changes                       | Yes          | —              |
| R16 | 4.6          | Invalid, missing or out-of-range date links                    | Yes          | —              |
| R17 | 4.7          | Ties ordered by creation                                       | Yes          | —              |
| R18 | 4.8          | Refresh about once a minute and on return                      | Yes          | —              |
| R19 | 4.8          | List stays visible during refresh; failure leaves it unchanged | Yes          | —              |
| R20 | 4.9          | Empty and error states                                         | Yes          | —              |
| R21 | 4.10         | Same page for everyone                                         | Yes          | —              |
| R22 | 4.11         | No payment instructions or skill level on cards                | Yes          | —              |

## 2. Test scenarios

### 2.1 Backend tests

| #   | Scenario                                       | Requirements | Test exists? | Result |
|-----|------------------------------------------------|---|--------------|--------|
| 1   | Signed out and signed in see the same games    | R21 | Yes          | Pass   |
| 6   | Mix of official, community and nonpublic games | R6, R10 | Yes          | Pass   |
| 7   | Registration cutoff                            | R10, R11 | Yes          | Pass   |
| 8   | Full games with and without a waitlist         | R12 | Yes          | Pass   |
| 9   | Confirmed players and guests                   | R13 | Yes          | Pass   |
| 10  | Hold during checkout and after it expires      | R13 | Yes          | Pass   |
| 11  | Official and community card contents           | R8 | Yes          | Pass   |
| 13  | No payment instructions or skill level         | R22 | Yes          | Pass   |
| 15  | Ordering and ties                              | R17 | Yes          | Pass   |
| 16  | Hour totals with more games than one batch     | R5, R7 | Yes          | Pass   |
| 18  | More than 40 games                             | R7 | Yes          | Pass   |
| 20  | Date before today or past the window           | R16 | Yes          | Pass   |
| 22  | Daylight saving and other device timezones     | R14 | Yes          | Pass   |
| 23  | Exactly 40 games                               | R7 | Yes          | Pass   |
| 26  | Game becomes ineligible before Load More       | R7 | Yes          | Pass   |
| 33  | Game beyond the 14-day window                  | R1, R10 | Yes          | Pass   |
| 35  | Game listed under its own local date           | R14 | Yes          | Pass   |

### 2.2 Frontend tests

| #   | Scenario                                       | Requirements | Test exists? | Result |
|-----|------------------------------------------------|---|--------------|--------|
| 2   | No date opens today                            | R4 | Yes          | Pass   |
| 3   | Valid date link                                | R4 | Yes          | Pass   |
| 4   | Date strip across its full range               | R1, R2, R3 | Yes          | Pass   |
| 5   | Selecting another date                         | R3, R4 | Yes          | Pass   |
| 8   | Full games with and without a waitlist         | R12 | Yes          | Pass   |
| 11  | Official and community card contents           | R8 | Yes          | Pass   |
| 12  | Cards with and without an image                | R8 | Yes          | Pass   |
| 14  | Selecting a card                               | R9 | Yes          | Pass   |
| 16  | Hour totals with more games than one batch     | R5 | Yes          | Pass   |
| 17  | Date with no games                             | R20 | Yes          | Pass   |
| 18  | More than 40 games                             | R7 | Yes          | Pass   |
| 19  | Opening an invalid date link                   | R16 | Yes          | Pass   |
| 20  | Date before today or past the window           | R16 | Yes          | Pass   |
| 21  | Page open across midnight                      | R15 | Yes          | Pass   |
| 22  | Daylight saving and other device timezones     | R14 | Yes          | Pass   |
| 23  | Exactly 40 games                               | R7 | Yes          | Pass   |
| 24  | First load fails, then Retry                   | R20 | Yes          | Pass   |
| 25  | Load More fails, then Retry                    | R7, R20 | Yes          | Pass   |
| 27  | Changing date while a request is pending       | R4 | Yes          | Pass   |
| 28  | Refresh while Load More is pending             | R7, R19 | Yes          | Pass   |
| 29  | Refresh picks up changes                       | R18 | Yes          | Pass   |
| 30  | Refreshing an expanded list                    | R7, R19 | Yes          | Pass   |
| 31  | Background refresh fails                       | R19 | Yes          | Pass   |
| 32  | Keyboard and screen reader use                 | R1, R7, R20 | Yes          | Pass   |
| 34  | Hold expires on a full game while page is open | R13 | Yes          | Pass   |
| 36  | Invalid date link while the page is open       | R16 | Yes          | Pass   |

## 3. Work to do

Item 1 was found in the 2026-11-18 review and is done.

1. Refresh the list once when the player returns to the page. Returning to the window used to start two refreshes, one when the window regained focus and one when the tab became visible. Update the frontend scenario 29 test to check that a return refreshes exactly once.
