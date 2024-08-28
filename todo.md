tests

- - scoring works, might need to change current orchestrator code a lot for this - but try to minimise ✅
- - query node non streaming (e.g. proteus text to image) ✅
- - plug into real servers for miner  (text: ✅, image: ✅ image-to-image: inpaint: ✅avatar: ✅) 
- - entry node redone (text: ✅, text-to-image: : ✅ image-to-image: inpaint:  avatar: )
- - Fix orchestrator for real scoring
- - end to end tests with real orchestrator
- - Make the weight setting make sense
- - look at my notes on phone
- - make so you can access the subnet with tao & tao only
- - scoring table for historic stuff



curl https://openrouter.ai/api/v1/chat/completions -H "Content-Type: application/json" -H "Authorization: Bearer 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" -d '{
  "messages": [
    {
      "role": "system",
      "content": "You are a test assistant."
    },
    {
      "role": "user",
      "content": "Testing. Just say hi and nothing else."
    }
  ],
  "model": "openai/gpt-4o"
}'