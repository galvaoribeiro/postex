"use client";

import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input, Label, Textarea } from "@/components/ui/input";
import type { ContentFormat } from "@/lib/api/types";

// Espelha `backend/app/ai/schemas.py` (ReelPayload, ImagePostPayload,
// CarouselPayload, StoryPayload). O payload e um JSONB livre no backend; estes
// tipos existem so no frontend para guiar o editor.

export interface ReelScene {
  order: number;
  duration_seconds: number;
  visual: string;
  on_screen_text: string;
  voiceover: string;
}
export interface ReelPayload {
  hook: string;
  scenes: ReelScene[];
  total_duration_seconds: number;
  music_suggestion: string;
  editing_notes: string;
}

export interface ImagePostPayload {
  headline: string;
  on_image_text: string;
  body_text: string;
  visual_direction: string;
}

export interface CarouselSlide {
  order: number;
  title: string;
  body: string;
  on_image_text: string;
}
export interface CarouselPayload {
  cover_title: string;
  slides: CarouselSlide[];
  visual_direction: string;
}

export interface StoryFrame {
  order: number;
  visual: string;
  text: string;
  interaction: string;
}
export interface StoryPayload {
  frames: StoryFrame[];
  visual_direction: string;
}

type AnyPayload = Record<string, unknown>;

export function PayloadEditor({
  format,
  payload,
  onChange,
}: {
  format: ContentFormat;
  payload: AnyPayload;
  onChange: (next: AnyPayload) => void;
}) {
  switch (format) {
    case "REEL":
      return (
        <ReelEditor
          payload={payload as unknown as ReelPayload}
          onChange={onChange as unknown as (p: ReelPayload) => void}
        />
      );
    case "IMAGE_POST":
      return (
        <ImagePostEditor
          payload={payload as unknown as ImagePostPayload}
          onChange={onChange as unknown as (p: ImagePostPayload) => void}
        />
      );
    case "CAROUSEL":
      return (
        <CarouselEditor
          payload={payload as unknown as CarouselPayload}
          onChange={onChange as unknown as (p: CarouselPayload) => void}
        />
      );
    case "STORY":
      return (
        <StoryEditor
          payload={payload as unknown as StoryPayload}
          onChange={onChange as unknown as (p: StoryPayload) => void}
        />
      );
    default:
      return null;
  }
}

function ReelEditor({ payload, onChange }: { payload: ReelPayload; onChange: (p: ReelPayload) => void }) {
  const scenes = payload.scenes ?? [];

  function updateScene(index: number, patch: Partial<ReelScene>) {
    const next = scenes.map((scene, i) => (i === index ? { ...scene, ...patch } : scene));
    onChange({ ...payload, scenes: next });
  }

  function addScene() {
    onChange({
      ...payload,
      scenes: [
        ...scenes,
        { order: scenes.length + 1, duration_seconds: 5, visual: "", on_screen_text: "", voiceover: "" },
      ],
    });
  }

  function removeScene(index: number) {
    onChange({ ...payload, scenes: scenes.filter((_, i) => i !== index).map((s, i) => ({ ...s, order: i + 1 })) });
  }

  return (
    <div className="space-y-5">
      <div>
        <Label>Gancho (primeiros 3 segundos)</Label>
        <Textarea rows={2} value={payload.hook ?? ""} onChange={(e) => onChange({ ...payload, hook: e.target.value })} />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <Label className="mb-0">Cenas</Label>
          <Button type="button" size="sm" variant="outline" icon={<Plus className="h-3.5 w-3.5" />} onClick={addScene}>
            Adicionar cena
          </Button>
        </div>
        <div className="space-y-3">
          {scenes.map((scene, index) => (
            <div key={index} className="rounded-xl border border-border-subtle p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground/50">Cena {scene.order}</span>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    min={1}
                    max={60}
                    value={scene.duration_seconds}
                    onChange={(e) => updateScene(index, { duration_seconds: Number(e.target.value) })}
                    className="h-7 w-16 text-xs"
                  />
                  <span className="text-xs text-foreground/40">seg</span>
                  <button onClick={() => removeScene(index)} className="text-foreground/40 hover:text-danger-fg" aria-label="Remover cena">
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
              <div className="space-y-2">
                <Textarea
                  rows={2}
                  placeholder="O que a camera mostra"
                  value={scene.visual}
                  onChange={(e) => updateScene(index, { visual: e.target.value })}
                />
                <Input
                  placeholder="Texto na tela"
                  value={scene.on_screen_text}
                  onChange={(e) => updateScene(index, { on_screen_text: e.target.value })}
                />
                <Input
                  placeholder="Narracao / fala"
                  value={scene.voiceover}
                  onChange={(e) => updateScene(index, { voiceover: e.target.value })}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label>Duracao total (seg)</Label>
          <Input
            type="number"
            min={5}
            max={180}
            value={payload.total_duration_seconds ?? 0}
            onChange={(e) => onChange({ ...payload, total_duration_seconds: Number(e.target.value) })}
          />
        </div>
        <div>
          <Label>Sugestao de musica</Label>
          <Input
            value={payload.music_suggestion ?? ""}
            onChange={(e) => onChange({ ...payload, music_suggestion: e.target.value })}
          />
        </div>
      </div>
      <div>
        <Label>Notas de edicao</Label>
        <Textarea
          rows={2}
          value={payload.editing_notes ?? ""}
          onChange={(e) => onChange({ ...payload, editing_notes: e.target.value })}
        />
      </div>
    </div>
  );
}

function ImagePostEditor({
  payload,
  onChange,
}: {
  payload: ImagePostPayload;
  onChange: (p: ImagePostPayload) => void;
}) {
  return (
    <div className="space-y-4">
      <div>
        <Label>Headline</Label>
        <Input value={payload.headline ?? ""} onChange={(e) => onChange({ ...payload, headline: e.target.value })} />
      </div>
      <div>
        <Label>Texto sobre a imagem</Label>
        <Textarea
          rows={2}
          value={payload.on_image_text ?? ""}
          onChange={(e) => onChange({ ...payload, on_image_text: e.target.value })}
        />
      </div>
      <div>
        <Label>Texto de apoio</Label>
        <Textarea
          rows={3}
          value={payload.body_text ?? ""}
          onChange={(e) => onChange({ ...payload, body_text: e.target.value })}
        />
      </div>
      <div>
        <Label>Direcao de arte</Label>
        <Textarea
          rows={2}
          value={payload.visual_direction ?? ""}
          onChange={(e) => onChange({ ...payload, visual_direction: e.target.value })}
        />
      </div>
    </div>
  );
}

function CarouselEditor({
  payload,
  onChange,
}: {
  payload: CarouselPayload;
  onChange: (p: CarouselPayload) => void;
}) {
  const slides = payload.slides ?? [];

  function updateSlide(index: number, patch: Partial<CarouselSlide>) {
    onChange({ ...payload, slides: slides.map((slide, i) => (i === index ? { ...slide, ...patch } : slide)) });
  }

  function addSlide() {
    onChange({
      ...payload,
      slides: [...slides, { order: slides.length + 1, title: "", body: "", on_image_text: "" }],
    });
  }

  function removeSlide(index: number) {
    onChange({ ...payload, slides: slides.filter((_, i) => i !== index).map((s, i) => ({ ...s, order: i + 1 })) });
  }

  return (
    <div className="space-y-5">
      <div>
        <Label>Titulo da capa</Label>
        <Input value={payload.cover_title ?? ""} onChange={(e) => onChange({ ...payload, cover_title: e.target.value })} />
      </div>

      <div>
        <div className="mb-2 flex items-center justify-between">
          <Label className="mb-0">Slides</Label>
          <Button type="button" size="sm" variant="outline" icon={<Plus className="h-3.5 w-3.5" />} onClick={addSlide}>
            Adicionar slide
          </Button>
        </div>
        <div className="space-y-3">
          {slides.map((slide, index) => (
            <div key={index} className="rounded-xl border border-border-subtle p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground/50">Slide {slide.order}</span>
                <button onClick={() => removeSlide(index)} className="text-foreground/40 hover:text-danger-fg" aria-label="Remover slide">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-2">
                <Input
                  placeholder="Titulo do slide"
                  value={slide.title}
                  onChange={(e) => updateSlide(index, { title: e.target.value })}
                />
                <Textarea
                  rows={2}
                  placeholder="Corpo do slide"
                  value={slide.body}
                  onChange={(e) => updateSlide(index, { body: e.target.value })}
                />
                <Input
                  placeholder="Texto sobre a imagem"
                  value={slide.on_image_text}
                  onChange={(e) => updateSlide(index, { on_image_text: e.target.value })}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <Label>Direcao de arte</Label>
        <Textarea
          rows={2}
          value={payload.visual_direction ?? ""}
          onChange={(e) => onChange({ ...payload, visual_direction: e.target.value })}
        />
      </div>
    </div>
  );
}

function StoryEditor({ payload, onChange }: { payload: StoryPayload; onChange: (p: StoryPayload) => void }) {
  const frames = payload.frames ?? [];

  function updateFrame(index: number, patch: Partial<StoryFrame>) {
    onChange({ ...payload, frames: frames.map((frame, i) => (i === index ? { ...frame, ...patch } : frame)) });
  }

  function addFrame() {
    onChange({
      ...payload,
      frames: [...frames, { order: frames.length + 1, visual: "", text: "", interaction: "nenhum" }],
    });
  }

  function removeFrame(index: number) {
    onChange({ ...payload, frames: frames.filter((_, i) => i !== index).map((f, i) => ({ ...f, order: i + 1 })) });
  }

  return (
    <div className="space-y-5">
      <div>
        <div className="mb-2 flex items-center justify-between">
          <Label className="mb-0">Frames</Label>
          <Button type="button" size="sm" variant="outline" icon={<Plus className="h-3.5 w-3.5" />} onClick={addFrame}>
            Adicionar frame
          </Button>
        </div>
        <div className="space-y-3">
          {frames.map((frame, index) => (
            <div key={index} className="rounded-xl border border-border-subtle p-3">
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold text-foreground/50">Frame {frame.order}</span>
                <button onClick={() => removeFrame(index)} className="text-foreground/40 hover:text-danger-fg" aria-label="Remover frame">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
              <div className="space-y-2">
                <Textarea
                  rows={2}
                  placeholder="O que aparece no frame"
                  value={frame.visual}
                  onChange={(e) => updateFrame(index, { visual: e.target.value })}
                />
                <Input
                  placeholder="Texto do frame"
                  value={frame.text}
                  onChange={(e) => updateFrame(index, { text: e.target.value })}
                />
                <Input
                  placeholder="Interacao: enquete, caixinha, link, quiz, nenhum"
                  value={frame.interaction}
                  onChange={(e) => updateFrame(index, { interaction: e.target.value })}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div>
        <Label>Direcao de arte</Label>
        <Textarea
          rows={2}
          value={payload.visual_direction ?? ""}
          onChange={(e) => onChange({ ...payload, visual_direction: e.target.value })}
        />
      </div>
    </div>
  );
}
