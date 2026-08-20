# Text-to-Video Endpoints

Curated picks across 4 use cases. **ByteDance Seedance 2.0** is the dominant premium choice; **Kling V3/O3** specializes in multi-shot and 4K; **Hailuo 2.3** is a strong newcomer for both premium and fast. Verify with `genmedia models --endpoint_id <id> --json` before running.

## Premium realism

Final-quality video.

- `bytedance/seedance-2.0/text-to-video`: ByteDance · Seedance 2.0
- `fal-ai/bytedance/seedance/v1.5/pro/text-to-video`: ByteDance · Seedance 1.5 Pro
- `fal-ai/veo3.1`: Google · Veo 3.1
- `fal-ai/kling-video/v3/pro/text-to-video`: Kling · V3 Pro
- `fal-ai/kling-video/o3/pro/text-to-video`: Kling · O3 Pro
- `fal-ai/minimax/hailuo-2.3/pro/text-to-video`: Minimax · Hailuo 2.3 Pro
- `google/gemini-omni-flash`: Google · Gemini Omni Flash (reasoning-based, audio included)

## Fast / cheap drafts

Fast motion preview, economical drafts.

- `bytedance/seedance-2.0/fast/text-to-video`: ByteDance · Seedance 2.0 Fast
- `fal-ai/bytedance/seedance/v1/pro/fast/text-to-video`: ByteDance · Seedance 1 Pro Fast
- `xai/grok-imagine-video/text-to-video`: xAI · Grok Imagine
- `fal-ai/veo3.1/lite`: Google · Veo 3.1 Lite
- `fal-ai/kling-video/v3/standard/text-to-video`: Kling · V3 Standard
- `fal-ai/kling-video/o3/standard/text-to-video`: Kling · O3 Standard
- `fal-ai/minimax/hailuo-2.3/standard/text-to-video`: Minimax · Hailuo 2.3 Standard

## 4K capable

Endpoints with native 4K output.

- `fal-ai/kling-video/v3/4k/text-to-video`: Kling · V3 4K
- `fal-ai/kling-video/o3/4k/text-to-video`: Kling · O3 4K

## Multi-shot / storytelling

Multi-shot / element / timeline support.

- `fal-ai/kling-video/v3/pro/text-to-video`: Kling · V3 Pro
- `fal-ai/kling-video/v3/standard/text-to-video`: Kling · V3 Standard
- `bytedance/seedance-2.0/text-to-video`: ByteDance · Seedance 2.0
- `alibaba/happy-horse/text-to-video`: Alibaba · Happy Horse
- `fal-ai/wan/v2.7/text-to-video`: Alibaba · Wan 2.7
- `google/gemini-omni-flash`: Google · Gemini Omni Flash (single-call storyboard input — pass a sequence of reference images)

## Reasoning-based (world knowledge, conversational)

Endpoints that use the model's reasoning to fill in unspecified visual
detail. The inverse of prescriptive prompt families like Kling and Seedance.

- `google/gemini-omni-flash`: Google · Gemini Omni Flash
- `fal-ai/veo3.1`: Google · Veo 3.1 (same family, less capable)

Use when the brief can lean on world knowledge ("a 1960s diner") rather
than enumerating visual facts.

## Family-specific prompting

For prompt-craft details, see `fal-prompting`:

- Kling family → [fal-prompting/references/kling.md](../../fal-prompting/references/kling.md)
- Happy Horse → [fal-prompting/references/happy-horse.md](../../fal-prompting/references/happy-horse.md)
- Gemini Omni → [fal-prompting/references/gemini-omni.md](../../fal-prompting/references/gemini-omni.md)

## Discovery

```bash
genmedia models --category text-to-video --limit 10 --json
genmedia docs "text to video" --json
```
