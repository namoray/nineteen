# Solution: Improved Selection of Miners for Queries Using Time-Decayed Period Scores

## Overview

This solution enhances the selection process of miners for both organic and synthetic queries by integrating time-decayed period scores. The goal is to ensure high-quality responses for users while promoting exploration for new miners, all while accurately reflecting miners' recent historical performance.

## Key Improvements

1. **Time-Decayed Historical Period Scores**

   - **Organic Queries**: Prioritize miners based on their time-decayed historical period scores, emphasizing recent performance.
   - **Separate Decay Factors**: Utilize separate decay factors for discrete periods (used in score calculations) and continuous time intervals (used in contender selection), ensuring appropriate weighting over time.

2. **Differentiated Selection Criteria**

   - **Organic Queries**: Miners with higher time-decayed historical period scores are prioritized to deliver top-quality responses to users.
   - **Synthetic Queries**: Miners with fewer total requests made are prioritized to assess and evaluate less-experienced or new miners.

3. **Promoting Exploration of New Miners**

   - By filling the unfulfilled slots with miners with fewer requests made, we promote the exploration of new miners, giving them the chance to also build their scores with organic queries.

## Benefits
- **Enhanced Response Quality**: Users receive high-quality answers from miners who have demonstrated strong performance in their recent history.
- **Exploration of New Miners**: New and less-assessed miners gain opportunities to participate also in organic queries to build their scores.
- **System Efficiency**: Optimized database queries enhance performance and scalability.


PD: "seasoning" :) 
