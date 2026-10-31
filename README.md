# GetYr_ECE – "How It Works" automation

A copy of the story-channel automation, set up for the electronics channel. Every hour,
cron-job.org starts **Actions → Daily video**. A new episode is made about every 6 hours (4 a day),
and 2 are published a day (12:00 and 18:00 India time), each with a vertical Short.

1. **Topic:** the next device or idea from `pipeline/electronics.py` (fan, charger, AirPods,
   laptop, transformer, ...), never repeated (`state/used_topics.json`).
2. **Script:** an accurate, in-depth explanation for students (NVIDIA API), then a strict
   engineering fact-check pass.
3. **Video:** a NotebookLM cinematic video in an educational animation style. The website
   removes the watermark, then the intro, outro and the corner text GetYr_ECE are added.
4. **Upload:** an SEO title and description, the title-screen thumbnail, and scheduling.
   NotebookLM's own Short (or a clip cut from the episode) is uploaded with it.

Setup and fixes: see `MAINTENANCE.md`. Content modes: `CONTENT_MODE` = `electronics` (default),
`stories` or `series`.
