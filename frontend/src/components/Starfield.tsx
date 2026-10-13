import { useEffect, useRef } from 'react';
import { useFieldMode } from '../theme/useFieldMode';

interface Star {
  x: number;
  y: number;
  r: number;
  baseAlpha: number;
  phase: number;
  speed: number;
}

interface Meteor {
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  maxLife: number;
}

/**
 * Canvas starfield with twinkling stars and occasional meteors.
 * Renders once (static) when the user prefers reduced motion.
 */
export default function Starfield({ density = 1, className = '' }: { density?: number; className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { fieldMode } = useFieldMode();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let stars: Star[] = [];
    let meteors: Meteor[] = [];
    let raf = 0;
    let width = 0;
    let height = 0;

    const seed = () => {
      const count = Math.floor((width * height) / 6500 * density);
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * width,
        y: Math.random() * height,
        r: Math.random() * 1.4 + 0.3,
        baseAlpha: Math.random() * 0.6 + 0.25,
        phase: Math.random() * Math.PI * 2,
        speed: Math.random() * 1.2 + 0.3,
      }));
    };

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
    };

    const tint = () => (fieldMode ? '255, 140, 128' : '235, 240, 255');

    const draw = (t: number) => {
      ctx.clearRect(0, 0, width, height);
      const c = tint();
      for (const s of stars) {
        const tw = reduced ? 1 : 0.65 + 0.35 * Math.sin(s.phase + t * 0.001 * s.speed);
        ctx.globalAlpha = s.baseAlpha * tw * (fieldMode ? 0.5 : 1);
        ctx.fillStyle = `rgb(${c})`;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;

      if (!reduced) {
        if (Math.random() < 0.008 && meteors.length < 2) {
          const mx = Math.random() * width * 0.8 + width * 0.1;
          meteors.push({ x: mx, y: -10, vx: -(4 + Math.random() * 3), vy: 3 + Math.random() * 2, life: 0, maxLife: 60 + Math.random() * 30 });
        }
        meteors = meteors.filter((m) => m.life < m.maxLife);
        for (const m of meteors) {
          m.x += m.vx;
          m.y += m.vy;
          m.life += 1;
          const fade = 1 - m.life / m.maxLife;
          const grad = ctx.createLinearGradient(m.x, m.y, m.x - m.vx * 12, m.y - m.vy * 12);
          grad.addColorStop(0, `rgba(${c},${0.9 * fade})`);
          grad.addColorStop(1, `rgba(${c},0)`);
          ctx.strokeStyle = grad;
          ctx.lineWidth = 1.6;
          ctx.beginPath();
          ctx.moveTo(m.x, m.y);
          ctx.lineTo(m.x - m.vx * 12, m.y - m.vy * 12);
          ctx.stroke();
        }
      }
    };

    resize();
    window.addEventListener('resize', resize);

    if (reduced) {
      draw(0);
    } else {
      const loop = (t: number) => {
        draw(t);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    return () => {
      window.removeEventListener('resize', resize);
      cancelAnimationFrame(raf);
    };
  }, [density, fieldMode]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
    />
  );
}
