# Solution: Optimized Selection of Miners for Queries

## Overview

This solution enhances the selection process of miners for both organic and synthetic queries. The goal is to ensure high-quality responses for users while providing promoting exploration for new miners.

## Key Improvements

1. **Differentiated Selection Criteria**

   - **Organic Queries**: Prioritize miners with higher performance scores (`PERIOD_SCORE`) to ensure users receive top-quality responses.
   - **Synthetic Queries**: Prioritize miners with fewer total requests made (`TOTAL_REQUESTS_MADE`) to assess and evaluate less-experienced or new miners.

2. **Two-Step Contender Selection Process**

   For both organic and synthetic queries, a two-step process is implemented:

   - **Initial Query**: Select miners based on the primary criterion for the query type.
     - *Organic Queries*: Highest `PERIOD_SCORE`.
     - *Synthetic Queries*: Least `TOTAL_REQUESTS_MADE`.
   - **Secondary Query**: If the initial query doesn't yield enough miners (`top_x`), fill the remaining slots by selecting miners with the least `TOTAL_REQUESTS_MADE`. This ensures the inclusion of newer miners.

3. **Promoting New Miners**

   - By prioritizing miners with fewer total requests in the secondary query for both query types, the system ensures new miners are given opportunities to participate, allowing them to build performance history and improve their scores.

4. **Weighted Scoring Based on Query Type**

   - Assign higher weights to performance data from organic queries in scoring calculations. This emphasizes the importance of real user interactions in evaluating miner performance over synthetic assessments.

5. **Efficient Database Operations**

   - Utilize indexed columns (`PERIOD_SCORE` and `TOTAL_REQUESTS_MADE`) in queries to optimize database performance and ensure quick retrieval of contenders.

## Detailed Selection Process

### Initial Query

- **Organic Queries**

  - **Objective**: Deliver responses from the best-performing miners to users.
  - **Selection Criterion**: Miners are ranked and selected based on the highest `PERIOD_SCORE`.

- **Synthetic Queries**

  - **Objective**: Assess and evaluate miners who have had fewer opportunities.
  - **Selection Criterion**: Miners are ranked and selected based on the least `TOTAL_REQUESTS_MADE`.

### Secondary Query

- **Purpose**: Ensure the required number of miners (`top_x`) is met if the initial query doesn't return enough contenders.
- **Selection Criterion for Both Query Types**:

  - Miners are selected based on the least `TOTAL_REQUESTS_MADE`.
  - **Benefit**: Promotes exploration by including newer or less-assessed miners, helping them build performance history.

## Benefits

- **Improved Response Quality**: Users receive high-quality answers from top-performing miners in organic queries.
- **Exploration of New Miners**: New and less-assessed miners gain opportunities to participate, especially in synthetic queries.
- **Balanced Evaluation**: Weighted scoring ensures that performance in organic queries has a greater impact on miners' overall scores.
- **System Efficiency**: Optimized database queries enhance performance and scalability.
