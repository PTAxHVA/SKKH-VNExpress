"use client";

import { Maximize, Pause, Play, Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useInView } from "react-intersection-observer";
import { Button } from "@/components/ui/button";

interface VideoPlayerProps {
  src: string;
  poster: string;
}

export function VideoPlayer({ src, poster }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const frameRef = useRef<HTMLDivElement>(null);
  const { ref, inView } = useInView({ triggerOnce: true, rootMargin: "200px" });
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const sync = () => {
      setCurrentTime(video.currentTime);
      setDuration(video.duration || 0);
      setIsPlaying(!video.paused);
    };
    video.addEventListener("timeupdate", sync);
    video.addEventListener("loadedmetadata", sync);
    video.addEventListener("play", sync);
    video.addEventListener("pause", sync);
    return () => {
      video.removeEventListener("timeupdate", sync);
      video.removeEventListener("loadedmetadata", sync);
      video.removeEventListener("play", sync);
      video.removeEventListener("pause", sync);
    };
  }, []);

  const togglePlay = async () => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) await video.play();
    else video.pause();
  };

  const toggleMute = () => {
    const video = videoRef.current;
    if (!video) return;
    video.muted = !video.muted;
    setIsMuted(video.muted);
  };

  const seek = (value: string) => {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = Number(value);
    setCurrentTime(video.currentTime);
  };

  const fullscreen = async () => {
    await frameRef.current?.requestFullscreen();
  };

  return (
    <div ref={ref} className="rounded-[32px] border border-line-subtle bg-bg-elevated/70 p-3 shadow-card-dark">
      <div ref={frameRef} className="overflow-hidden rounded-[24px] bg-black">
        <video
          ref={videoRef}
          src={inView ? src : undefined}
          poster={poster}
          preload="metadata"
          playsInline
          className="aspect-video w-full bg-black object-cover"
          aria-label="Video mô phỏng SUMO so sánh Fixed-Time và Q-Learning"
        />
        <div className="flex flex-wrap items-center gap-3 border-t border-white/10 bg-bg-base/95 p-4">
          <Button variant="icon" onClick={togglePlay} aria-label={isPlaying ? "Tạm dừng video" : "Phát video"}>
            {isPlaying ? <Pause className="size-4" /> : <Play className="size-4 fill-current" />}
          </Button>
          <input
            aria-label="Tua video"
            className="min-w-40 flex-1 accent-[var(--accent-bio)]"
            type="range"
            min={0}
            max={duration || 0}
            step={0.1}
            value={currentTime}
            onChange={(event) => seek(event.target.value)}
          />
          <span className="font-mono text-xs text-ink-secondary">
            {formatTime(currentTime)} / {formatTime(duration)}
          </span>
          <Button variant="icon" onClick={toggleMute} aria-label={isMuted ? "Bật âm thanh" : "Tắt âm thanh"}>
            {isMuted ? <VolumeX className="size-4" /> : <Volume2 className="size-4" />}
          </Button>
          <Button variant="icon" onClick={fullscreen} aria-label="Xem toàn màn hình">
            <Maximize className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

function formatTime(value: number) {
  if (!Number.isFinite(value)) return "00:00";
  const minutes = Math.floor(value / 60).toString().padStart(2, "0");
  const seconds = Math.floor(value % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}
