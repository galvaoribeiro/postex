"""Brief visual concentrado: modelo + produto + video.

Um bloco so, no estilo do CREATIVE_BRIEF antigo. Os builders de imagem e
video so injetam fatos da campanha (produto, marca, destino, duracao) no
topo; a direcao visual nao se espalha por varios arquivos.
"""

from __future__ import annotations

from app.ai.content_engine import ProductionResult
from app.ai.context_builder import BusinessContext
from app.models.enums import CampaignDestination

CREATIVE_MARKER = "CREATIVE BRIEF"

HARD_SAFETY = (
    "18+ ONLY. If a person appears, they must be a fictional adult clearly "
    "over 25 years old. Not a lookalike of any real celebrity. Fully clothed; "
    "garments stay on."
)

STILL_NEGATIVE = (
    "child, underage, teen, celebrity lookalike, AI-looking face, plastic skin, "
    "doll-like appearance, excessive beauty retouching, unrealistic hourglass, "
    "exaggerated breasts or hips, distorted hands, extra fingers, duplicated limbs, "
    "warped phone, incorrect mirror reflection, duplicated objects, floating objects, "
    "impossible clothing, glossy CGI, 3D render, illustration, anime, professional "
    "studio backdrop, luxury mansion aesthetic, cinematic lighting, neon lights, "
    "excessive bokeh, text overlay, captions, logos invented, watermarks, "
    "interface elements, nudity, lingerie, celebrity"
)

VIDEO_NEGATIVE = (
    "child, underage, teen, celebrity lookalike, scene cuts, jump cuts, "
    "external camera movement, location changes, product morphing, identity changes, "
    "face changes, body transformation, text overlay, captions, watermarks, "
    "TikTok interface, muted video, silent clip, no audio, off-camera narrator, "
    "robotic text-to-speech, dancing, extra fingers, duplicated limbs, "
    "warped product, floating objects, product duplication, mirror distortion, "
    "phone duplication, cinematic lighting, slow motion, studio fashion aesthetic"
)

# ---------------------------------------------------------------------------
# Bloco unico: criar a modelo (Image A)
# ---------------------------------------------------------------------------

CHARACTER_BRIEF = f"""\
{CREATIVE_MARKER}

CRIANDO A MODELO
AGE

18

HAIR COLOR

BROWN

OTHER CHARACTERISTICS

TANNED ARM


Create an ultra-photorealistic vertical 9:16 mirror selfie of an attractive adult Brazilian woman with a feminine,
natural, fit and believable appearance.

She must clearly look like a real Brazilian woman rather than a fashion render or AI-generated model.

Respect exactly the age, hair color and additional characteristics provided above.

She is standing naturally in front of a full-length mirror inside her own home in Brazil, casually taking a mirror
selfie with an orange iPhone 17.

The phone must look authentic, correctly proportioned and physically believable in her hand. She is holding it
naturally at approximately upper-chest or face height while looking at the phone screen through the mirror.

This image will later be used as the reference character for realistic product demonstrations, advertisements,
social-media videos and lifestyle content.

Her identity, facial features, hairstyle, body proportions, skin tone and overall appearance must therefore be
clearly defined and visually consistent.

Give her realistic anatomy, natural body proportions, believable skin texture, realistic hands and fingers,
natural facial asymmetry and authentic human characteristics.

Her pose should already resemble the opening frame of a casual TikTok or Instagram product video.

She should look confident, natural and approachable. Her free hand should remain naturally positioned in a way
that allows it to interact with a future product when necessary.

Do not force a specific interaction yet because the product will be introduced later.

Dress her in a simple, neutral and fashionable outfit appropriate for an adult woman.

The outfit should be visually clean and versatile so that different products can later be introduced without
creating visual conflicts.

The environment must feel unmistakably like a real, ordinary Brazilian home rather than a luxury apartment,
professional photography studio, hotel or influencer set.

Use a modest and familiar residential interior:

light painted walls
simple ceramic or porcelain tile flooring
normal wooden or white interior door
basic bedroom or dressing furniture
wardrobe or dresser partially visible
large ordinary full-length mirror
small everyday household details

Keep the room slightly imperfect and genuinely lived-in.

Include subtle believable details such as simple bedding, a charging cable, sandals, a small object on a dresser
or another harmless everyday item.

Do not make the room dirty, cluttered or distracting.

Nothing should look carefully staged for a commercial advertisement.

Use natural Brazilian home lighting.

Soft daylight may enter from an unseen window combined with subtle indoor ambient lighting.

Avoid cinematic studio lighting, colored LEDs, dramatic rim lights, beauty lighting, artificial glow or luxury
commercial aesthetics.

The image should feel as if she casually opened her camera and took the photo herself at home.

PHOTOGRAPHIC LOOK

Realistic smartphone photography captured with an iPhone 17-class camera.

Natural computational HDR.
Realistic skin texture.
Subtle pores.
Tiny imperfections.
Realistic hair strands.
Believable fabric texture.
Accurate reflections.
Natural exposure.
Moderate smartphone sharpening.
Realistic dynamic range.
Subtle sensor processing.

Keep the image clean and high quality but NOT professionally polished.

Do not use extreme background blur.

Most of the room should remain reasonably recognizable, as expected from a normal smartphone mirror photo.

The mirror reflection must be physically accurate.

Her body, hands, fingers, smartphone, clothing, room geometry and reflection must all be coherent.

The orange iPhone 17 must appear only where physically appropriate and must never be duplicated.

Frame her approximately from head to knees or almost full body, with enough surrounding environment visible
to establish that she is inside a real Brazilian home.

Keep her as the obvious focal point while preserving the amateur mirror-selfie feeling.

Her expression should be relaxed, confident and natural.

Avoid exaggerated influencer expressions, duck face or an artificial fashion-model stare.


CRITICAL REALISM RULES

photorealistic adult human
real skin texture
anatomically correct body
anatomically correct hands and fingers
natural facial asymmetry
realistic Brazilian residential environment
accurate mirror physics
correct smartphone reflection
realistic body proportions
believable gravity
natural posture
authentic amateur smartphone composition


AVOID

AI-looking face
plastic skin
doll-like appearance
excessive beauty retouching
unrealistic anatomy
distorted hands
extra fingers
duplicated limbs
warped phone
incorrect mirror reflection
duplicated objects
floating objects
impossible geometry
glossy CGI appearance
3D render
illustration
anime
professional studio backdrop
luxury mansion aesthetic
cinematic lighting
neon lights
excessive bokeh
text
captions
logos
watermarks
interface elements


RESULTADO FINAL

Aspect ratio: 9:16 vertical.

Final result: an extremely realistic adult Brazilian woman casually taking a mirror selfie at home, visually
indistinguishable from an authentic smartphone photo taken by a real person in Brazil.

The image must provide a stable and consistent human reference for subsequent product integration and video
generation.
"""

# ---------------------------------------------------------------------------
# Integracao Image A (modelo) + Image B (produto)
# ---------------------------------------------------------------------------

PRODUCT_INTEGRATION_BRIEF = """\
INTEGRAÇÃO IMAGEM MODELO E PRODUTO/SERVIÇO

Use Image A as the main identity and scene reference (the woman, mirror,
orange iPhone 17, Brazilian home, lighting and photographic style described
in CRIANDO A MODELO).

Use Image B as the product, brand, service or visual-reference source.

The final result must preserve the woman from Image A while intelligently
integrating the subject represented by Image B into the scene.

IMAGE A — WOMAN AND SCENE
Preserve: face, identity, hair, skin tone, body proportions, physical
appearance, general pose, home environment, mirror, smartphone, lighting,
photographic style, overall visual identity.

IMAGE B — PRODUCT / SERVICE REFERENCE
Image B is the primary reference for the product, brand, service or visual
subject that must be integrated.

Do NOT copy the person appearing in Image B.
If Image B contains a person, use only the relevant product, object, garment,
packaging, logo, visual identity or other requested subject from that image.
The person from Image B must NOT appear in the final result unless explicitly
requested.

INTELLIGENT PRODUCT INTERPRETATION
First analyze what the subject in Image B represents (physical consumer
product, bottle, food, cosmetics, perfume, clothing, jewelry, handbag,
electronics, appliance, package, digital product, service, brand concept, or
another commercial object). Then choose the most natural and visually
believable way for the woman to interact with or present that subject.
Do NOT blindly place every product in her hand. The interaction must make
physical and semantic sense.

PHYSICAL PRODUCT RULES
If Image B represents a physical product, preserve it as accurately as
possible: exact product identity, shape, dimensions, proportions, colors,
materials, surface, texture, packaging, label, branding, logos, typography
when visible, closures, caps, buttons, screens, ports, handles, straps and
distinctive details.

Do not redesign the product.
Do not invent a different product.
Do not replace the product with a generic object.
Do not change its brand identity.
Do not create additional copies unless multiple units are clearly required.

INTELLIGENT INTERACTION
Bottle or beverage: hold it, present it toward the mirror/camera, or prepare
to drink it.
Perfume: hold near her chest, present toward the mirror, or apply it.
Cosmetics: hold near her face, present it, or demonstrate use.
Phone or device: hold, inspect, or present toward the mirror.
Handbag: carry on the shoulder or hold by the handle.
Footwear: worn on the feet, not artificially held.
Jewelry: worn on the appropriate body part.
Glasses: worn on her face.
Clothing: exact garment on the woman, identity and body proportions preserved.
Food: held, presented, served or consumed believably.
Tool: in hand only if that is a natural use; otherwise in the environment.
Appliance, furniture or large object: in the environment at believable scale,
not forced into her hands.
Digital product, software, app or online service: do not invent a physical
object unless the reference clearly contains one. She may use a smartphone,
tablet or computer when appropriate.
Service with no physical product: a natural real-world situation that
communicates the service without a fake product.

PHYSICAL REALISM
Respect realistic scale, weight, gravity, grip points, hand positioning,
finger placement, contact surfaces, occlusion, shadows, reflections,
perspective, depth and material behavior. The product must actually exist
inside the scene. Hands wrap around objects when appropriate. Objects must
not float, pass through hands, merge with the body, appear duplicated or
change shape.

COMPOSITION
Ultra-photorealistic vertical 9:16 mirror-selfie. Preserve the natural
Brazilian home from Image A. The woman remains the primary human subject.
The product or service representation becomes the primary commercial subject.
Both coexist naturally. Authentic social-media content, not a professional
photoshoot. Emphasize the product without looking artificially staged.

PRODUCT VISIBILITY
The product must be clearly recognizable. Important details from Image B
remain readable whenever physically possible. Do not cover logos, labels or
distinctive features. Small product: hold closer to the mirror. Large
product: composition that shows its full form. Two hands if required. Wear
it if it should be worn. Place it in the environment if that is natural.

IDENTITY CONSISTENCY
The woman from Image A remains the same person. Do not change face, hair,
skin tone, body proportions, age, identity or general appearance. Do not
introduce the person from Image B.

CAMERA AND MIRROR
Maintain the orange iPhone 17. The phone must remain physically believable.
Accurate mirror geometry. She is still taking the photo herself through the
mirror. There is no external photographer.

RESULTADO FINAL
An ultra-realistic 9:16 smartphone mirror selfie of the exact woman from
Image A naturally interacting with, using, wearing, presenting or being
accompanied by the exact product, service or commercial subject represented
by Image B. Physically believable, commercially useful and naturally created
for social media.
"""

APPROVED_MODEL_AS_IMAGE_A = """\
ATTACHED IMAGE A = the approved woman already generated for this brand.
Preserve her exact face, hair, body, skin, identity, clothing silhouette,
mirror scene and photographic style. Do not invent a new person. Image A is
the identity lock for the final still.
"""

REFERENCE_AS_IMAGE_B = """\
GENERATED RESULT = a 9:16 mirror selfie of the woman (CRIANDO A MODELO)
together with the commercial subject. Never output a product-only packshot,
a floating bottle on white, or a catalog crop. The woman must remain in frame.

ATTACHED PHOTO = visual source for the commercial subject (packaging, garment,
object, logo, food, device). It may contain extra people, hands or background.
Do not copy those people. Extract and preserve the commercial subject:
same shape, color, packaging, labels and distinctive details. Restage that
subject into the woman's mirror selfie. This is not a background edit and not
a product redesign.
"""

NO_REFERENCE_PRODUCT = """\
No photo was attached. The generated result is still the woman in the
Brazilian home mirror selfie — never a product-only image. Invent a
physically believable commercial subject that matches the name and
description in the campaign header. Do not invent a different brand.
Present it naturally according to INTELLIGENT INTERACTION.
"""


def _offering_line(context: BusinessContext) -> str:
    focused = next((item for item in context.products if item.is_focus), None)
    focused_service = next((item for item in context.services if item.is_focus), None)
    offering = focused or focused_service
    if offering is None:
        return (
            f"Subject: the brand {context.name} ({context.segment}). "
            "No invented product packaging."
        )
    kind = "Product" if focused is not None else "Service"
    extra = f" {offering.description}" if getattr(offering, "description", None) else ""
    return (
        f"{kind} in frame (Image B): '{offering.name}'.{extra} "
        "Show the real offering honestly; do not invent labels or claims."
    )


def _visual_from_production(production: ProductionResult) -> str:
    payload = production.fields.get("payload") or {}
    bits: list[str] = []
    for key in ("title", "concept"):
        value = production.fields.get(key)
        if value:
            bits.append(str(value))
    for key in ("hook", "visual_direction", "headline", "cover_title"):
        value = payload.get(key)
        if value:
            bits.append(str(value))
    scenes = payload.get("scenes") or payload.get("frames") or payload.get("slides") or []
    if scenes and isinstance(scenes[0], dict):
        visual = scenes[0].get("visual") or scenes[0].get("body") or scenes[0].get("title")
        if visual:
            bits.append(str(visual))
    return " ".join(bits)[:900]


def spoken_intent(production: ProductionResult) -> str:
    """Gancho da peca para virar fala curta no video (nao texto na tela)."""
    payload = production.fields.get("payload") or {}
    for key in ("hook", "headline", "cover_title"):
        value = payload.get(key) or production.fields.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:180]
    scenes = payload.get("scenes") or payload.get("frames") or []
    if scenes and isinstance(scenes[0], dict):
        voiceover = scenes[0].get("voiceover") or scenes[0].get("hook")
        if isinstance(voiceover, str) and voiceover.strip():
            return voiceover.strip()[:180]
    return ""


def campaign_header(
    *,
    context: BusinessContext,
    production: ProductionResult,
    destination: CampaignDestination | None = None,
    duration_seconds: int | None = None,
) -> str:
    dest_label = (
        destination.value.replace("_", " ").title() if destination else "Instagram"
    )
    location = context.location or "Brazil"
    lines = [
        f"CAMPAIGN for {dest_label}: {context.name}, a {context.segment} in {location}.",
        _offering_line(context),
    ]
    scene = _visual_from_production(production)
    if scene:
        lines.append(f"Copy direction (do not render as on-screen text): {scene}")
    if duration_seconds:
        lines.append(f"Clip length: {duration_seconds} seconds, one continuous take.")
    lines.append(
        "The product, props and background MUST match this business. "
        "Do not substitute a gym, boutique, studio or generic lifestyle set "
        "unless that is this business."
    )
    return "\n".join(lines)


def still_creative_block(*, has_reference: bool, has_model: bool = False) -> str:
    lead = REFERENCE_AS_IMAGE_B if has_reference else NO_REFERENCE_PRODUCT
    parts = [lead.strip()]
    if has_model:
        parts.insert(0, APPROVED_MODEL_AS_IMAGE_A.strip())
    else:
        parts.append(CHARACTER_BRIEF.strip())
    parts.append(PRODUCT_INTEGRATION_BRIEF.strip())
    return "\n\n".join(parts)


def video_creative_block(
    *,
    duration_seconds: int,
    has_reference: bool,
    spoken_intent: str = "",
    speech_language: str = "en",
) -> str:
    del has_reference
    fidelity = (
        "IMAGE-TO-VIDEO. The attached image is the generated starting frame: "
        "the woman, the product, the orange iPhone 17, the mirror and the "
        "Brazilian home. Animate THAT frame. Do not invent a new person, do "
        "not switch location, do not replace the product. Her face, hairstyle, "
        "skin tone, body proportions, clothing, product appearance, accessories "
        "and room must remain consistent with the attached still throughout the "
        "entire video. The product in the still is already correct. Do NOT "
        "redesign, replace, recolor, deform or reinterpret it."
    )
    spoken_lang = "brazilian portuguese" if speech_language == "pt" else "lowercase english"
    spoken = (
        f"Campaign line to adapt into spoken {spoken_lang} (do not burn as "
        f"on-screen text): {spoken_intent.strip()}"
        if spoken_intent.strip()
        else (
            f"Invent one short product line in {spoken_lang} that fits this "
            "exact offering. Do not invent discounts or fake brand claims."
        )
    )
    voice_rule = (
        "She speaks casual brazilian portuguese, on camera, matching the lips."
        if speech_language == "pt"
        else (
            "Kling native speech is english or chinese; write the dialogue in "
            "lowercase english (uppercase only for product names). Lips must "
            "match the words."
        )
    )
    return f"""\
{CREATIVE_MARKER}

VIDEO COM ROSTO

Create an ultra-photorealistic {duration_seconds}-second vertical 9:16
product-focused social-media video.

{fidelity}

Preserve the product's exact shape, proportions, colors, materials, surface,
branding, packaging, label, logo, visible text, distinctive details, buttons,
caps, handles, screens and straps.

PRODUCT-AWARE PERFORMANCE
The woman should naturally interact with the product according to what the
product actually is. Do not use a generic clothing-try-on sequence. The video
should look like a real person casually creating TikTok, Instagram Reels or
TikTok Shop content inside her own home. Spontaneous, not choreographed.

GENERAL MOVEMENT PRINCIPLE
Something should subtly change every approximately 0.5–1.5 seconds: posture,
hand position, product position, product angle, distance from mirror, facial
expression, gaze, body orientation or product interaction.

{_video_timeline(duration_seconds)}

NATIVE AUDIO
The clip must have a real soundtrack. Do not generate a silent or muted video.

Ambient bed: quiet ordinary Brazilian home — room tone, faint street, fabric,
product handling, a soft phone tap. Keep it documentary, not a music-video mix.

On-camera voice: she speaks naturally while looking at the phone or mirror.
{voice_rule}
One or two short lines, then a natural pause. No off-camera narrator.
No robotic text-to-speech. No burned-in captions.

{spoken}

CAMERA AND MIRROR BEHAVIOR
The smartphone remains naturally held in one hand whenever physically
possible. Tiny realistic handheld movements from her arm and body. The camera
must NOT behave like an external cameraman. This is a mirror selfie recorded
by the woman herself. Accurate mirror reflections. The orange iPhone 17 must
never duplicate, warp or change appearance.

PRODUCT CONSISTENCY
No product morphing, shape/label/logo/color/material/packaging/size changes,
missing or new components, or duplicate products.

PHYSICAL REALISM
Realistic grip, correct fingers, believable weight, correct scale, accurate
perspective, natural shadows, realistic reflections, correct occlusion,
realistic product physics, natural body movement.

REALISM
Extremely realistic smartphone video, natural iPhone-style processing, real
skin texture, natural hair physics, realistic product materials, correct
anatomy, authentic indoor smartphone footage. Keep the slightly amateur,
casual social-media quality of a real TikTok or Instagram video. Do NOT add
cinematic depth of field, dramatic camera movements, studio lighting, slow
motion, artificial beauty filters or commercial fashion aesthetics.

Use one continuous {duration_seconds}-second take.

RESULTADO FINAL
A highly believable viral-style social-media product video showing the exact
woman and exact product, with ambient home sound and her own spoken voice.
She naturally interacts with, presents, demonstrates, wears or uses the
product according to its actual nature. The product remains clearly
recognizable and visually consistent throughout the continuous recording.
"""


def _video_timeline(duration_seconds: int) -> str:
    total = max(4, int(duration_seconds))
    marks = [0.0, 0.10, 0.20, 0.32, 0.45, 0.58, 0.72, 0.83, 0.92, 1.0]
    beats = [
        "Begin directly from the reference pose. The product is immediately visible and clearly recognizable. She looks at the phone screen or mirror.",
        "Small natural movement; slightly adjust posture or product position. Product remains clearly visible.",
        "Naturally interact with or present the product. Use an interaction appropriate to the actual product, not a generic gesture.",
        "Subtly move the product closer to the mirror or adjust her body to show an important product feature.",
        "Change the angle of the product or her body slightly, revealing another useful visual aspect. Natural hands, realistic object physics.",
        "Continue the product interaction. If useful, show another angle, demonstrate use, or reveal an important feature.",
        "Small natural adjustment to the product, posture or hand placement. Do not freeze.",
        "Return toward a natural front-facing or product-focused composition.",
        "Finish with a clean, natural pose in which the product remains clearly visible. Expression natural and confident.",
    ]
    lines = [f"{total}-SECOND PERFORMANCE"]
    for index, beat in enumerate(beats):
        start = marks[index] * total
        end = marks[index + 1] * total
        lines.append(f"{start:.1f}–{end:.1f}s  {beat}")
    return "\n".join(lines)
