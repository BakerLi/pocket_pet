# Credits & third-party assets

Pocket Pet's code is original. Some **artwork is not** — it is reused from
third parties under their terms and credited here.

## Rabbit sprite art — "Light Brown Bunny"

The rabbit graphics in `assets/sprites/rabbit/` are derived from the
**Light Brown Bunny** Shimeji image set (resized/cropped and repacked into
sprite sheets; the artwork itself is unchanged in style and not original to
this project).

- **Artist:** FluffyFoxOfFate — https://www.deviantart.com/fluffyfoxoffate
  (support: https://ko-fi.com/fluffyfoxoffate)
- **Framework:** Shimeji-ee (Shimeji English Enhanced) by **Kilkakon** —
  https://kilkakon.com/shimeji
- **Original Shimeji:** Yuki Yamada / Group Finity —
  http://www.group-finity.com/Shimeji/

Per the Shimeji-ee pack's `licence.txt` (by Kilkakon):

> You are welcome to use this work in your own projects if you credit Kilkakon
> and the original people who worked on this. A link to kilkakon.com would also
> be nice.

### Shimeji-ee licence (source/framework)

```
Copyright (c) Shimeji-ee Group
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this
list of conditions and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this
list of conditions and the following disclaimer in the documentation and/or
other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

## Procedurally-drawn art

All other species (and the egg + baby forms) are drawn at runtime with QPainter
in `src/pocket_pet/ui/sprite.py` — original to this project.
