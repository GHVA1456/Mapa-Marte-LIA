// WebGL terrain is uploaded once. Each frame updates only the camera and sunlight.
function createGroundRenderer(canvas, dem, dx, dy) {
  const gl = canvas.getContext("webgl", {alpha: false, antialias: true});
  if (!gl) return null;

  const skyVertex = [
    "attribute vec2 aPosition;",
    "varying vec2 vScreen;",
    "void main() { vScreen = aPosition; gl_Position = vec4(aPosition, 0.0, 1.0); }",
  ].join("\n");
  const skyFragment = [
    "precision highp float;",
    "varying vec2 vScreen;",
    "uniform vec3 uRight, uUp, uForward, uSun;",
    "uniform vec2 uFocal;",
    "uniform float uDay;",
    "void main() {",
    "  vec3 ray = normalize(uForward + uRight * vScreen.x / uFocal.x + uUp * vScreen.y / uFocal.y);",
    "  vec3 horizon = mix(vec3(0.10, 0.12, 0.18), vec3(0.82, 0.52, 0.37), uDay);",
    "  vec3 zenith = mix(vec3(0.018, 0.026, 0.060), vec3(0.35, 0.19, 0.17), uDay);",
    "  vec3 color = mix(horizon, zenith, pow(max(ray.z, 0.0), 0.45));",
    "  float distanceToSun = length(ray - uSun);",
    "  float aboveHorizon = smoothstep(-0.015, 0.015, uSun.z) * uDay;",
    "  float glow = exp(-distanceToSun * 13.0) * 0.50;",
    "  float disk = 1.0 - smoothstep(0.003, 0.007, distanceToSun);",
    "  gl_FragColor = vec4(mix(color, vec3(1.0, 0.90, 0.69), aboveHorizon * min(1.0, glow + disk)), 1.0);",
    "}",
  ].join("\n");
  const terrainVertex = [
    "attribute vec3 aPosition, aNormal;",
    "uniform vec3 uEye, uRight, uUp, uForward;",
    "uniform vec2 uFocal;",
    "varying vec3 vNormal;",
    "varying vec2 vGrid;",
    "varying float vDepth, vHeight;",
    "void main() {",
    "  vec3 offset = aPosition - uEye;",
    "  float depth = dot(offset, uForward);",
    "  gl_Position = vec4(dot(offset, uRight) * uFocal.x, dot(offset, uUp) * uFocal.y, 1.0003 * depth - 0.9, depth);",
    "  vNormal = aNormal; vGrid = aPosition.xy; vDepth = depth; vHeight = aPosition.z;",
    "}",
  ].join("\n");
  const terrainFragment = [
    "precision highp float;",
    "uniform vec3 uSun;",
    "uniform float uDay, uTextureReady, uDetailReady;",
    "uniform vec4 uUvScale, uDetailUv;",
    "uniform sampler2D uMosaic, uDetail;",
    "varying vec3 vNormal;",
    "varying vec2 vGrid;",
    "varying float vDepth, vHeight;",
    "void main() {",
    "  vec2 uv = uUvScale.xy + vGrid * uUvScale.zw;",
    "  vec4 sampleColor = texture2D(uMosaic, uv);",
    "  vec2 detailUv = uDetailUv.xy + vGrid * uDetailUv.zw;",
    "  vec4 detail = texture2D(uDetail, detailUv);",
    "  vec2 edge = min(detailUv, 1.0 - detailUv);",
    "  float detailWeight = uDetailReady * detail.a * smoothstep(0.0, 0.11, min(edge.x, edge.y));",
    "  float heightTint = clamp((vHeight + 2640.0) / 160.0, 0.0, 1.0);",
    "  vec3 base = mix(vec3(0.47, 0.235, 0.13), vec3(0.76, 0.48, 0.29), heightTint);",
    "  vec3 textureColor = sampleColor.rgb;",
    "  base = mix(base, textureColor, uTextureReady * sampleColor.a);",
    "  vec3 detailColor = detail.rgb;",
    "  base = mix(base, detailColor, detailWeight);",
    "  float sunLight = max(dot(normalize(vNormal), uSun), 0.0) * smoothstep(-0.01, 0.12, uSun.z);",
    "  vec3 lit = base * (0.22 + 0.56 * uDay + 0.30 * uDay * sunLight);",
    "  lit *= mix(vec3(0.52, 0.69, 1.02), vec3(1.0), uDay);",
    "  vec3 dust = mix(vec3(0.095, 0.105, 0.15), vec3(0.78, 0.48, 0.33), uDay);",
    "  gl_FragColor = vec4(mix(lit, dust, min(0.65, 1.0 - exp(-max(vDepth, 0.0) / 9000.0))), 1.0);",
    "}",
  ].join("\n");

  function makeProgram(vertexSource, fragmentSource, uniforms) {
    const program = gl.createProgram();
    for (const [type, source] of [[gl.VERTEX_SHADER, vertexSource], [gl.FRAGMENT_SHADER, fragmentSource]]) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return null;
      gl.attachShader(program, shader);
      gl.deleteShader(shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return null;
    return {program, uniforms: Object.fromEntries(uniforms.map(name => [name, gl.getUniformLocation(program, name)]))};
  }

  const shared = ["uRight", "uUp", "uForward", "uFocal", "uSun", "uDay"];
  const sky = makeProgram(skyVertex, skyFragment, shared);
  const terrain = makeProgram(terrainVertex, terrainFragment, [
    ...shared, "uEye", "uTextureReady", "uUvScale", "uMosaic", "uDetailReady", "uDetailUv", "uDetail",
  ]);
  if (!sky || !terrain) return null;

  const positions = new Float32Array(dem.rows * dem.cols * 6);
  const indices = [];
  for (let row = 0; row < dem.rows; row++) {
    const north = Math.max(0, row - 1), south = Math.min(dem.rows - 1, row + 1);
    for (let col = 0; col < dem.cols; col++) {
      const west = Math.max(0, col - 1), east = Math.min(dem.cols - 1, col + 1);
      const gradientX = (dem.grid[row][east] - dem.grid[row][west]) / ((east - west) * dx);
      const gradientY = (dem.grid[north][col] - dem.grid[south][col]) / ((south - north) * dy);
      const id = row * dem.cols + col;
      positions.set([col * dx, -row * dy, dem.grid[row][col], -gradientX, -gradientY, 1], id * 6);
      if (row + 1 < dem.rows && col + 1 < dem.cols) {
        indices.push(id, id + 1, id + dem.cols, id + 1, id + dem.cols + 1, id + dem.cols);
      }
    }
  }

  function upload(target, data) {
    const buffer = gl.createBuffer();
    gl.bindBuffer(target, buffer);
    gl.bufferData(target, data, gl.STATIC_DRAW);
    return buffer;
  }
  const mesh = upload(gl.ARRAY_BUFFER, positions);
  const elements = upload(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(indices));
  const backdrop = upload(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]));
  const skyPosition = gl.getAttribLocation(sky.program, "aPosition");
  const terrainPosition = gl.getAttribLocation(terrain.program, "aPosition");
  const terrainNormal = gl.getAttribLocation(terrain.program, "aNormal");

  function createTextureSlot(unit) {
    const texture = gl.createTexture();
    gl.activeTexture(gl.TEXTURE0 + unit);
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(4));
    return {texture, unit, mosaic: null, ready: false, uv: [0, 0, 0, 0]};
  }
  const baseSlot = createTextureSlot(0), detailSlot = createTextureSlot(1);
  const anisotropy = gl.getExtension("EXT_texture_filter_anisotropic");

  function refreshTexture(slot, mosaic) {
    if (!mosaic || mosaic.pending || !mosaic.loaded) return false;
    if (slot.mosaic === mosaic) return slot.ready;
    slot.mosaic = mosaic;
    slot.ready = false;
    const {sheet, u, v, stepU, stepV} = mosaic;
    try {
      gl.activeTexture(gl.TEXTURE0 + slot.unit);
      gl.bindTexture(gl.TEXTURE_2D, slot.texture);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, sheet);
      if (anisotropy) {
        gl.texParameterf(gl.TEXTURE_2D, anisotropy.TEXTURE_MAX_ANISOTROPY_EXT,
          Math.min(8, gl.getParameter(anisotropy.MAX_TEXTURE_MAX_ANISOTROPY_EXT)));
      }
      slot.uv = [(u + stepU / 2) / sheet.width, (v + stepV / 2) / sheet.height,
        stepU / (dx * sheet.width), -stepV / (dy * sheet.height)];
      slot.ready = true;
    } catch { /* If a texture is unavailable, keep rendering the measured terrain. */ }
    return slot.ready;
  }

  function draw({col, row, elevation, direction, sun, daylight, mosaic, detail}) {
    if (gl.isContextLost() || !canvas.clientWidth || !canvas.clientHeight) return false;
    const dpr = Math.min(window.devicePixelRatio || 1, 2, 2200 / canvas.clientWidth);
    const width = Math.round(canvas.clientWidth * dpr), height = Math.round(canvas.clientHeight * dpr);
    if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
    const yaw = direction * Math.PI / 180, pitch = Math.PI / 18;
    const sin = Math.sin(yaw), cos = Math.cos(yaw), sinPitch = Math.sin(pitch), cosPitch = Math.cos(pitch);
    const right = [cos, -sin, 0], up = [sin * sinPitch, cos * sinPitch, cosPitch];
    const forward = [sin * cosPitch, cos * cosPitch, -sinPitch];
    const focal = [1.46, 1.46 * width / height];
    const applyCamera = ({program, uniforms}) => {
      gl.useProgram(program);
      gl.uniform3fv(uniforms.uRight, right);
      gl.uniform3fv(uniforms.uUp, up);
      gl.uniform3fv(uniforms.uForward, forward);
      gl.uniform2fv(uniforms.uFocal, focal);
      gl.uniform3fv(uniforms.uSun, sun);
      gl.uniform1f(uniforms.uDay, daylight);
    };
    gl.viewport(0, 0, width, height);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.disable(gl.DEPTH_TEST);
    applyCamera(sky);
    gl.bindBuffer(gl.ARRAY_BUFFER, backdrop);
    gl.enableVertexAttribArray(skyPosition);
    gl.vertexAttribPointer(skyPosition, 2, gl.FLOAT, false, 0, 0);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
    gl.disableVertexAttribArray(skyPosition);

    gl.enable(gl.DEPTH_TEST);
    applyCamera(terrain);
    const baseReady = refreshTexture(baseSlot, mosaic), detailReady = refreshTexture(detailSlot, detail);
    gl.uniform3f(terrain.uniforms.uEye, col * dx, -row * dy, elevation + 1.7);
    gl.uniform1i(terrain.uniforms.uMosaic, 0);
    gl.uniform1f(terrain.uniforms.uTextureReady, baseReady ? 1 : 0);
    gl.uniform4fv(terrain.uniforms.uUvScale, baseSlot.uv);
    gl.uniform1i(terrain.uniforms.uDetail, 1);
    gl.uniform1f(terrain.uniforms.uDetailReady, detailReady ? 1 : 0);
    gl.uniform4fv(terrain.uniforms.uDetailUv, detailSlot.uv);
    gl.bindBuffer(gl.ARRAY_BUFFER, mesh);
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, elements);
    gl.enableVertexAttribArray(terrainPosition);
    gl.enableVertexAttribArray(terrainNormal);
    gl.vertexAttribPointer(terrainPosition, 3, gl.FLOAT, false, 24, 0);
    gl.vertexAttribPointer(terrainNormal, 3, gl.FLOAT, false, 24, 12);
    gl.drawElements(gl.TRIANGLES, indices.length, gl.UNSIGNED_SHORT, 0);
    gl.disableVertexAttribArray(terrainPosition);
    gl.disableVertexAttribArray(terrainNormal);
    return true;
  }

  return {draw, hasTexture: () => baseSlot.ready, hasDetail: mosaic => detailSlot.mosaic === mosaic && detailSlot.ready};
}
