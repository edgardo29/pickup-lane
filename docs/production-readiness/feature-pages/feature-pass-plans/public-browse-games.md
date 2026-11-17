# F15 — Browse Games Feature Pass Plan

**Page specification:** `docs/production-readiness/feature-pages/pages/public/browse-games.md`  
**Endpoints:** `GET /games/browse`

## 1. Page requirements

| Spec section | Requirement                                                    | In the code? | What's missing |
|--------------|----------------------------------------------------------------|--------------|----------------|
| 3.1          | 14 dates in two sets of seven                                  | Yes          | —              |
| 3.1          | Arrows switch sets, not the selected date                      | Yes          | —              |
| 3.1          | Strip shows the set containing the selected date               | Yes          | —              |
| 3.1          | Opens on today; date kept in the link                          | Yes          | —              |
| 3.2          | Grouped by start hour with hour totals                         | Yes          | —              |
| 3.2          | Official and community games in one list                       | Yes          | —              |
| 3.2          | Batches of 40 with Load More                                   | Yes          | —              |
| 3.3          | Card contents                                                  | Yes          | —              |
| 3.4          | Card opens Game Details                                        | Yes          | —              |
| 4.1          | Which games appear                                             | Yes          | —              |
| 4.2          | Registration cutoff 5 minutes after start                      | Yes          | —              |
| 4.3          | Full games stay listed, no waitlist badge                      | Yes          | —              |
| 4.4          | Spot counts, including unexpired holds                         | Yes          | —              |
| 4.5          | Market timezone for dates, times and hour groups               | Yes          | —              |
| 4.5          | Window moves when the market day changes                       | Yes          | —              |
| 4.6          | Invalid, missing or out-of-range date links                    | Yes          | —              |
| 4.7          | Ties ordered by creation                                       | Yes          | —              |
| 4.8          | Refresh about once a minute and on return                      | Yes          | —              |
| 4.8          | List stays visible during refresh; failure leaves it unchanged | Yes          | —              |
| 4.9          | Empty and error states                                         | Yes          | —              |
| 4.10         | Same page for everyone                                         | Yes          | —              |
| 4.11         | No payment instructions or skill level on cards                | Yes          | —              |

## 2. Test scenarios

### 2.1 Backend tests

| #   | Scenario                                       | Test exists? | Result |
|-----|------------------------------------------------|--------------|--------|
| 1   | Signed out and signed in see the same games    | Yes          | Pass   |
| 6   | Mix of official, community and nonpublic games | Yes          | Pass   |
| 7   | Registration cutoff                            | Yes          | Pass   |
| 8   | Full games with and without a waitlist         | Yes          | Pass   |
| 9   | Confirmed players and guests                   | Yes          | Pass   |
| 10  | Hold during checkout and after it expires      | Yes          | Pass   |
| 11  | Official and community card contents           | Yes          | Pass   |
| 13  | No payment instructions or skill level         | Yes          | Pass   |
| 15  | Ordering and ties                              | Yes          | Pass   |
| 16  | Hour totals with more games than one batch     | Yes          | Pass   |
| 18  | More than 40 games                             | Yes          | Pass   |
| 20  | Date before today or past the window           | Yes          | Pass   |
| 22  | Daylight saving and other device timezones     | Yes          | Pass   |
| 23  | Exactly 40 games                               | Yes          | Pass   |
| 26  | Game becomes ineligible before Load More       | Yes          | Pass   |
| 33  | Game beyond the 14-day window                  | Yes          | Pass   |
| 35  | Game listed under its own local date           | Yes          | Pass   |

### 2.2 Frontend tests

| #   | Scenario                                       | Test exists? | Result |
|-----|------------------------------------------------|--------------|--------|
| 2   | No date opens today                            | Yes          | Pass   |
| 3   | Valid date link                                | Yes          | Pass   |
| 4   | Date strip across its full range               | Yes          | Pass   |
| 5   | Selecting another date                         | Yes          | Pass   |
| 8   | Full games with and without a waitlist         | Yes          | Pass   |
| 11  | Official and community card contents           | Yes          | Pass   |
| 12  | Cards with and without an image                | Yes          | Pass   |
| 14  | Selecting a card                               | Yes          | Pass   |
| 16  | Hour totals with more games than one batch     | Yes          | Pass   |
| 17  | Date with no games                             | Yes          | Pass   |
| 18  | More than 40 games                             | Yes          | Pass   |
| 19  | Opening an invalid date link                   | Yes          | Pass   |
| 20  | Date before today or past the window           | Yes          | Pass   |
| 21  | Page open across midnight                      | Yes          | Pass   |
| 22  | Daylight saving and other device timezones     | Yes          | Pass   |
| 23  | Exactly 40 games                               | Yes          | Pass   |
| 24  | First load fails, then Retry                   | Yes          | Pass   |
| 25  | Load More fails, then Retry                    | Yes          | Pass   |
| 27  | Changing date while a request is pending       | Yes          | Pass   |
| 28  | Refresh while Load More is pending             | Yes          | Pass   |
| 29  | Refresh picks up changes                       | Yes          | Pass   |
| 30  | Refreshing an expanded list                    | Yes          | Pass   |
| 31  | Background refresh fails                       | Yes          | Pass   |
| 32  | Keyboard and screen reader use                 | Yes          | Pass   |
| 34  | Hold expires on a full game while page is open | Yes          | Pass   |
| 36  | Invalid date link while the page is open       | Yes          | Pass   |

## 3. Work to do

None. All work is done.
