# Copyright (C) 2025 AIDC-AI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Video Processing Service

基于 ffmpeg-python 封装的高性能视频处理和合成服务。

核心能力:
- 视频首尾拼接 (Concatenation)
- 音视频轨道合并及自动时长调节 (Audio/video merging)
- 叠加透明图像作为视频的字幕/排版层 (Image overlay)
- 背景音乐混合与循环控制 (Background music addition)
- 基于单张静态图像与音频创建流媒体视频段 (Image to video conversion)

注意: 运行此模块要求宿主系统已正确安装 FFmpeg 并且在环境变量 PATH 中可用。
"""

import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import List, Literal, Optional

import ffmpeg
from loguru import logger

from pixelle_video.utils.os_util import (
    get_resource_path,
    list_resource_files,
    resource_exists
)


def check_ffmpeg() -> None:
    """
    检查系统环境中是否安装了 FFmpeg 命令工具。
    
    Raises:
        RuntimeError: 如果系统中未找到 FFmpeg 抛出异常并提示安装方法。
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError(
            "FFmpeg not found. Please install it:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu/Debian: apt-get install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )


class VideoService:
    """
    Video compositor for common video processing tasks
    多功能视频合成处理类。

    Uses ffmpeg-python for high-performance video processing.
    采用 ffmpeg-python 库作为与底层 ffmpeg 命令交互的桥梁，所有的处理操作
    在条件允许的情况下都尽可能使用不重编码的轨道复制（stream copy），从而保证最高性能。

    Examples:
        >>> compositor = VideoService()
        >>>
        >>> # Concatenate videos / 拼接多个分镜视频为一个长视频
        >>> compositor.concat_videos(
        ...     ["intro.mp4", "main.mp4", "outro.mp4"],
        ...     "final.mp4"
        ... )
        >>>
        >>> # Add voiceover / 把生成的旁白语音塞入生成的无声画面视频中
        >>> compositor.merge_audio_video(
        ...     "visual.mp4",
        ...     "voiceover.mp3",
        ...     "final.mp4"
        ... )
        >>>
        >>> # Add background music / 添加背景音乐
        >>> compositor.add_bgm(
        ...     "video.mp4",
        ...     "music.mp3",
        ...     "final.mp4",
        ...     bgm_volume=0.3
        ... )
        >>>
        >>> # Create video from image + audio / 从静态图片创建视频
        >>> compositor.create_video_from_image(
        ...     "frame.png",
        ...     "narration.mp3",
        ...     "segment.mp4"
        ... )
        >>>
        >>> # Overlay composed frame on video / 把带排版的透明静态帧叠在底层视频上
        >>> compositor.overlay_image_on_video(...)
    """

    def __init__(self):
        self._ffmpeg_checked = False

    def _ensure_ffmpeg(self):
        """Lazily check FFmpeg availability on first use, not at import time"""
        if not self._ffmpeg_checked:
            check_ffmpeg()
            self._ffmpeg_checked = True

    def concat_videos(
        self,
        videos: List[str],
        output: str,
        method: Literal["demuxer", "filter"] = "demuxer",
        bgm_path: Optional[str] = None,
        bgm_volume: float = 0.2,
        bgm_mode: Literal["once", "loop"] = "loop"
    ) -> str:
        """
        Concatenate multiple videos into one / 将列表中的多个分段小视频拼接为一个完整的长视频文件，并可选择性地混入背景音乐。

        Args:
            videos: List of video file paths to concatenate / 待拼接的视频文件本地路径列表。
            output: Output video file path / 拼接完成后输出的最终视频保存路径。
            method: Concatenation method / 核心拼接策略：
                - "demuxer": Fast, no re-encoding (requires identical formats)
                - "filter": Slower but handles different formats
            bgm_path: Background music file path (optional) / 背景音乐文件路径（可选）。
                - None: No BGM
                - "default.mp3": Use built-in default BGM
                - Other string: Resolve to resource file
            bgm_volume: BGM volume factor (0.0 to 1.0) / 混入背景音乐的音量系数。
            bgm_mode: BGM playback mode / 背景音乐播完后的策略：
                - "once": Play once
                - "loop": Loop until video ends (default)

        Returns:
            str: Output file path / 成功后返回最终输出文件的路径。

        Raises:
            ValueError: Empty video list.
            RuntimeError: FFmpeg command failed.
        """
        self._ensure_ffmpeg()

        if not videos:
            raise ValueError("Videos list cannot be empty")
        
        if len(videos) == 1:
            logger.info(f"Only one video provided, copying to {output}")
            shutil.copy(videos[0], output)
            return output
        
        logger.info(f"Concatenating {len(videos)} videos using {method} method")
        
        # Step 1: 拼接所有纯视频轨道
        if bgm_path:
            # 如果需要后期混入 BGM，先拼接到一个临时文件
            temp_output = output.replace('.mp4', '_no_bgm.mp4')
            concat_result = self._concat_demuxer(videos, temp_output) if method == "demuxer" else self._concat_filter(videos, temp_output)
            
            # Step 2: 把刚刚拼接好的大长段拿来混入 BGM
            logger.info(f"Adding BGM: {bgm_path} (volume={bgm_volume}, mode={bgm_mode})")
            final_result = self._add_bgm_to_video(
                video=concat_result,
                bgm_path=bgm_path,
                output=output,
                volume=bgm_volume,
                mode=bgm_mode
            )
            
            # 清理无用的无 BGM 临时文件
            if os.path.exists(temp_output):
                os.unlink(temp_output)
            
            return final_result
        else:
            # 不需要 BGM，直接拼接输出到最终路径
            if method == "demuxer":
                return self._concat_demuxer(videos, output)
            else:
                return self._concat_filter(videos, output)
    
    def _concat_demuxer(self, videos: List[str], output: str) -> str:
        """
        使用 FFmpeg 的 concat demuxer 技术拼接视频（极速，免重编码）。
        
        内部原理相当于构造一个 txt 播放列表并执行:
            ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
        """
        # 创建包含所有待处理文件路径的临时配置文本
        with tempfile.NamedTemporaryFile(
            mode='w',
            delete=False,
            suffix='.txt',
            encoding='utf-8'
        ) as f:
            for video in videos:
                abs_path = Path(video).absolute()
                escaped_path = str(abs_path).replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
            filelist = f.name
        
        try:
            logger.debug(f"Created filelist: {filelist}")
            (
                ffmpeg
                .input(filelist, format='concat', safe=0)
                .output(output, c='copy')
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            logger.success(f"Videos concatenated successfully: {output}")
            return output
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg concat error: {error_msg}")
            raise RuntimeError(f"Failed to concatenate videos: {error_msg}")
        finally:
            if os.path.exists(filelist):
                os.unlink(filelist)
    
    def _concat_filter(self, videos: List[str], output: str) -> str:
        """
        使用 FFmpeg 的 complex_filter 技术拼接视频（极慢，但兼容任何输入格式的混剪）。
        
        内部原理:
            ffmpeg -i v1.mp4 -i v2.mp4 -filter_complex "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]"
                   -map "[v]" -map "[a]" output.mp4
        """
        try:
            n = len(videos)
            
            # 组装滤镜所需的输入流标识标签组: [0:v][0:a][1:v][1:a]...
            stream_spec = "".join([f"[{i}:v][{i}:a]" for i in range(n)])
            filter_complex = f"{stream_spec}concat=n={n}:v=1:a=1[v][a]"
            
            # 手动组装底层命令行，因为 python-ffmpeg 对长复杂滤镜链包装支持不够友好
            cmd = ['ffmpeg']
            for video in videos:
                cmd.extend(['-i', video])
            cmd.extend([
                '-filter_complex', filter_complex,
                '-map', '[v]',
                '-map', '[a]',
                '-y',  # 覆盖输出
                output
            ])
            
            import subprocess
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            logger.success(f"Videos concatenated successfully: {output}")
            return output
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            logger.error(f"FFmpeg concat filter error: {error_msg}")
            raise RuntimeError(f"Failed to concatenate videos: {error_msg}")
        except Exception as e:
            logger.error(f"Concatenation error: {e}")
            raise RuntimeError(f"Failed to concatenate videos: {e}")
    
    def _get_video_duration(self, video: str) -> float:
        """通过探测（probe）读取本地视频文件时长的辅助方法"""
        try:
            probe = ffmpeg.probe(video)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            logger.warning(f"Failed to get video duration: {e}")
            return 0.0
    
    def _get_audio_duration(self, audio: str) -> float:
        """通过探测读取本地音频文件时长的辅助方法，支持基于文件尺寸的粗略估计容错"""
        try:
            probe = ffmpeg.probe(audio)
            duration = float(probe['format']['duration'])
            return duration
        except Exception as e:
            logger.warning(f"Failed to get audio duration: {e}, using estimate")
            import os
            file_size = os.path.getsize(audio)
            # 假设 MP3 的平均码率为 16kbps，即 2KB 每秒
            estimated_duration = file_size / 2000
            return max(1.0, estimated_duration)
    
    def has_audio_stream(self, video: str) -> bool:
        """
        检查视频文件中是否内含音频轨道。
        
        Args:
            video: 视频文件路径
        
        Returns:
            bool: 含有音轨返回 True，静音视频返回 False
        """
        try:
            probe = ffmpeg.probe(video)
            audio_streams = [s for s in probe.get('streams', []) if s['codec_type'] == 'audio']
            has_audio = len(audio_streams) > 0
            logger.debug(f"Video {video} has_audio={has_audio}")
            return has_audio
        except Exception as e:
            logger.warning(f"Failed to probe video audio streams: {e}, assuming no audio")
            return False
    
    def merge_audio_video(
        self,
        video: str,
        audio: str,
        output: str,
        replace_audio: bool = True,
        audio_volume: float = 1.0,
        video_volume: float = 0.0,
        pad_strategy: str = "freeze",
        auto_adjust_duration: bool = True,
        duration_tolerance: float = 0.3,
    ) -> str:
        """
        合并分离的音轨与视频轨（常用于将 AI 旁白加到 AI 生成的默片上）。
        此方法拥有强大的智能时长协调能力。
        
        时长协调机制 (当 auto_adjust_duration=True 时):
        - 视频 < 音频：将视频结尾最后一帧冻结定格延长，直至匹配录音时长，避免出现读完无画面的黑屏。
        - 视频 > 音频 (在误差容忍度 duration_tolerance 之内)：不作处理，正常结合。
        - 视频 > 音频 (超出误差度)：裁剪掉后面多余的视频片段对齐。
        
        音轨接管策略:
        - 无声视频：直接将新音轨压入。
        - 视频已有声音 (replace_audio=True)：抹除视频自带的背景音（比如 AI 生视频的杂音），仅采用传入的新音频。
        - 视频已有声音 (replace_audio=False)：将视频原来的底噪环境音按设定的 video_volume 与新录音进行混流（amix）。
        
        Args:
            video: 目标视频文件。
            audio: 目标音频（旁白）文件。
            output: 最终输出路径。
            replace_audio: 是否强制替代掉原本的视频声音。
            audio_volume: 新音频（旁白）的主音量系数 (0.0-1.0+)。
            video_volume: 原本视频背景音的保留音量 (0.0-1.0+)。
            pad_strategy: 当视频短于音频时的填充策略：
                         - "freeze": 将原视频定格至最后一帧（默认）。
                         - "black": 使用纯黑屏来补全时间。
            auto_adjust_duration: 是否启动智能剪裁和填充策略（默认为 True）。
            duration_tolerance: 当视频偏长时，不被裁掉的宽限时间差（秒）。
        
        Returns:
            str: 成功合成的文件路径。
            
        Raises:
            RuntimeError: 当 FFmpeg 执行彻底失败时抛出。
        """
        self._ensure_ffmpeg()

        # Get durations of video and audio / 获取源音视频的具体精确秒数时长
        video_duration = self._get_video_duration(video)
        audio_duration = self._get_audio_duration(audio)
        
        logger.info(f"Video duration: {video_duration:.2f}s, Audio duration: {audio_duration:.2f}s")
        
        # 智能匹配协调时长
        if auto_adjust_duration:
            diff = video_duration - audio_duration
            
            if diff < 0:
                # 视频不够用：通过定格或黑屏垫满
                logger.warning(f"⚠️ Video shorter than audio by {abs(diff):.2f}s, padding required")
                video = self._pad_video_to_duration(video, audio_duration, pad_strategy)
                video_duration = audio_duration
                logger.info(f"📌 Padded video to {audio_duration:.2f}s")
            
            elif diff > duration_tolerance:
                # 视频长出太多：截断尾部画面
                logger.info(f"⚠️ Video longer than audio by {diff:.2f}s (tolerance: {duration_tolerance}s)")
                video = self._trim_video_to_duration(video, audio_duration)
                video_duration = audio_duration
                logger.info(f"✂️ Trimmed video to {audio_duration:.2f}s")
            
            else:
                # 稍微长一点点，在容忍范围内放行
                logger.info(f"✅ Duration acceptable: video={video_duration:.2f}s, audio={audio_duration:.2f}s (diff={diff:.2f}s)")
        
        target_duration = max(video_duration, audio_duration)
        logger.info(f"Target output duration: {target_duration:.2f}s")
        
        video_has_audio = self.has_audio_stream(video)
        
        input_video = ffmpeg.input(video)
        video_stream = input_video.video
        
        # 额外的异常状况安全网：假如前面的填充因为某些情况漏了，再次在滤镜上通过 tpad 进行流级填充
        if audio_duration > video_duration:
            pad_duration = audio_duration - video_duration
            logger.info(f"Audio is longer, padding video by {pad_duration:.2f}s using '{pad_strategy}' strategy")
            
            if pad_strategy == "freeze":
                video_stream = video_stream.filter('tpad', stop_mode='clone', stop_duration=pad_duration)
            else:  # black
                probe = ffmpeg.probe(video)
                video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                width = int(video_info['width'])
                height = int(video_info['height'])
                fps_str = video_info['r_frame_rate']
                fps_num, fps_den = map(int, fps_str.split('/'))
                fps = fps_num / fps_den if fps_den != 0 else 30
                
                black_video_path = self._get_unique_temp_path("black_pad", os.path.basename(output))
                black_input = ffmpeg.input(
                    f'color=c=black:s={width}x{height}:r={fps}',
                    f='lavfi',
                    t=pad_duration
                )
                video_stream = ffmpeg.concat(video_stream, black_input.video, v=1, a=0)
        
        # 准备要混入的音频流，带上静音垫底以防偶尔过短
        input_audio = ffmpeg.input(audio)
        audio_stream = input_audio.audio.filter('volume', audio_volume)
        
        if video_duration > audio_duration:
            pad_duration = video_duration - audio_duration
            logger.info(f"Video is longer, padding audio with {pad_duration:.2f}s silence")
            audio_stream = audio_stream.filter('apad', whole_dur=target_duration)
        
        # 状况A：视频原本是静音默片
        if not video_has_audio:
            logger.info(f"Video has no audio stream, adding audio track")
            try:
                (
                    ffmpeg
                    .output(
                        video_stream,
                        audio_stream,
                        output,
                        vcodec='libx264',
                        acodec='aac',
                        audio_bitrate='192k'
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                logger.success(f"Audio added to silent video: {output}")
                return output
            except ffmpeg.Error as e:
                error_msg = e.stderr.decode() if e.stderr else str(e)
                logger.error(f"FFmpeg error adding audio to silent video: {error_msg}")
                raise RuntimeError(f"Failed to add audio to video: {error_msg}")
        
        # 状况B：视频原本有声音
        logger.info(f"Merging audio with video (replace={replace_audio})")
        
        try:
            if replace_audio:
                # 舍弃原音频轨映射
                (
                    ffmpeg
                    .output(
                        video_stream,
                        audio_stream,
                        output,
                        vcodec='libx264',
                        acodec='aac',
                        audio_bitrate='192k'
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            else:
                # 保留并混合混叠两者的声音
                mixed_audio = ffmpeg.filter(
                    [
                        input_video.audio.filter('volume', video_volume),
                        audio_stream
                    ],
                    'amix',
                    inputs=2,
                    duration='longest'
                )
                
                (
                    ffmpeg
                    .output(
                        video_stream,
                        mixed_audio,
                        output,
                        vcodec='libx264',
                        acodec='aac',
                        audio_bitrate='192k'
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            
            logger.success(f"Audio merged successfully: {output}")
            return output
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg merge error: {error_msg}")
            raise RuntimeError(f"Failed to merge audio and video: {error_msg}")
    
    def overlay_image_on_video(
        self,
        video: str,
        overlay_image: str,
        output: str,
        scale_mode: str = "contain"
    ) -> str:
        """
        将带有透明通道的排版图片像盖滤镜一样叠加在动态视频上面。
        这是项目中非常重要的功能——它将 HTML 排版生成的精致画面安全框/装饰边框无缝贴合到底层视频之上。
        
        Args:
            video: 提供动态画面的底部基础视频文件。
            overlay_image: 带透明度 (Alpha) 的顶层叠加图片。
            output: 叠加完毕后输出的结果文件。
            scale_mode: 针对底层的视频缩放裁切策略（使其能适应透明安全框的大小）。
                - "contain": 以宽高等比缩小保证内容全露，并在空白处留黑边/白边（保证主旨完整）。
                - "cover": 放大并裁切多余的边缘区域使画面撑满框（不留黑边，但会遮挡部分主画面）。
                - "stretch": 不保比例暴力拉伸直到填满屏幕。
        
        Returns:
            str: 叠加完成后的视频文件地址。
            
        Raises:
            RuntimeError: FFmpeg 执行失败。
        """
        self._ensure_ffmpeg()
        logger.info(f"Overlaying image on video (scale_mode={scale_mode})")
        
        try:
            # 解析顶层叠加蒙版的宽和高，底部的动态视频必须主动去迎合这个尺寸约束
            overlay_probe = ffmpeg.probe(overlay_image)
            overlay_stream = next(s for s in overlay_probe['streams'] if s['codec_type'] == 'video')
            overlay_width = int(overlay_stream['width'])
            overlay_height = int(overlay_stream['height'])
            
            logger.debug(f"Overlay dimensions: {overlay_width}x{overlay_height}")
            
            input_video = ffmpeg.input(video)
            input_overlay = ffmpeg.input(overlay_image)
            
            # 根据提供的约束模式，给底层视频装载相应的滤镜指令链
            if scale_mode == "contain":
                # Scale to fit: 安全缩放，并在长宽无法对应时通过 pad 补充黑色底布
                scaled_video = (
                    input_video
                    .filter('scale', overlay_width, overlay_height, force_original_aspect_ratio='decrease')
                    .filter('pad', overlay_width, overlay_height, '(ow-iw)/2', '(oh-ih)/2', color='black')
                )
            elif scale_mode == "cover":
                # Scale to cover: 完全填满后截断边缘多余图像
                scaled_video = (
                    input_video
                    .filter('scale', overlay_width, overlay_height, force_original_aspect_ratio='increase')
                    .filter('crop', overlay_width, overlay_height)
                )
            else:  # stretch
                # 简单粗暴的强制重新规定分辨率
                scaled_video = input_video.filter('scale', overlay_width, overlay_height)
            
            # 使用 overlay filter 实现叠底
            output_stream = ffmpeg.overlay(scaled_video, input_overlay)
            
            (
                ffmpeg
                .output(output_stream, output, 
                        vcodec='libx264',
                        pix_fmt='yuv420p',
                        preset='medium',
                        crf=23)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.success(f"Image overlaid on video: {output}")
            return output
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg overlay error: {error_msg}")
            raise RuntimeError(f"Failed to overlay image on video: {error_msg}")
    
    def create_video_from_image(
        self,
        image: str,
        audio: str,
        output: str,
        fps: int = 30,
    ) -> str:
        """
        基于一张静态长图与配音录音文件合成一个具有对应时间流淌和帧率流的“伪视频”（实际上是静态轮播的视频）。
        主要用于静态模板 (image template) 以及没有选用生成底层视频模型的简化版场景中。
        
        Args:
            image: 用作视频帧基底的静态图片。
            audio: 旁白/配音的录音文件，它决定了这个生成的 MP4 视频究竟有多长。
            output: 最终存放结果的相对/绝对目录。
            fps: 输出成伪视频时所用的时间编码率（默认30）。
        
        Returns:
            str: 转换结束获得的视频路径。
        """
        self._ensure_ffmpeg()
        logger.info("Creating video from image and audio")
        
        try:
            # 探测这首配乐，以此完全界定我们要压出多长的帧
            probe = ffmpeg.probe(audio)
            audio_duration = float(probe['format']['duration'])
            logger.debug(f"Audio duration: {audio_duration:.3f}s")
            
            # 读图模式设定为 loop 循环无限读入，同时锁死流输入速度
            input_image = ffmpeg.input(image, loop=1, framerate=fps)
            input_audio = ffmpeg.input(audio)
            
            # 使用 -t 强制斩断并决定结束退出点
            (
                ffmpeg
                .output(
                    input_image,
                    input_audio,
                    output,
                    t=audio_duration,
                    vcodec='libx264',
                    acodec='aac',
                    pix_fmt='yuv420p',
                    audio_bitrate='192k',
                    preset='medium',
                    crf=23,
                    **{'b:v': '2M'}  # 提供可供普通流媒体播放的最低容忍度码率带宽
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.success(f"Video created from image: {output} (duration: {audio_duration:.3f}s)")
            return output
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg error creating video from image: {error_msg}")
            raise RuntimeError(f"Failed to create video from image: {error_msg}")
    
    def add_bgm(
        self,
        video: str,
        bgm: str,
        output: str,
        bgm_volume: float = 0.3,
        loop: bool = True,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
    ) -> str:
        """
        为完整的视频（通常是包含旁白的）混入全局的背景音乐 (BGM)。
        
        Args:
            video: 处理好的主体长视频对象。
            bgm: 全局环境配乐歌曲。
            output: 成果文件路径。
            bgm_volume: 对加入音乐的削弱/增强幅度系数。
            loop: 如果为 True（常见情形），一旦原版 BGM 时长过短将被无限拉长重播。
            fade_in: 入场时的音频淡入动效时间（秒）。
            fade_out: 离场时的淡出过渡时间（暂未开启复杂实现支持）。
        
        Returns:
            str: 打包混合后封装产生的新成果路径。
        """
        self._ensure_ffmpeg()
        logger.info(f"Adding BGM to video (volume={bgm_volume}, loop={loop})")
        
        try:
            input_video = ffmpeg.input(video)
            
            # 使用 ffmpeg 魔法标志 stream_loop=-1 实现媒体输入的无缝首尾重播延展
            bgm_input = ffmpeg.input(
                bgm,
                stream_loop=-1 if loop else 0
            )
            
            # 构建管道组：给音乐轨装配调音台滤镜组件
            bgm_audio = bgm_input.audio.filter('volume', bgm_volume)
            
            if fade_in > 0:
                bgm_audio = bgm_audio.filter('afade', type='in', duration=fade_in)
            
            # amix 管道混响指令，使用 input 集合并以最早消亡（通常指原始长视频的边界）的数据包时长作为界线退出
            mixed_audio = ffmpeg.filter(
                [input_video.audio, bgm_audio],
                'amix',
                inputs=2,
                duration='first'
            )
            
            (
                ffmpeg
                .output(
                    input_video.video,
                    mixed_audio,
                    output,
                    vcodec='copy',  # 由于前面所有的拼合均已就绪并对正，这里不需要重画，只需要原样照搬轨道参数进行重新多路转接
                    acodec='aac',
                    audio_bitrate='192k'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.success(f"BGM added successfully: {output}")
            return output
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg BGM error: {error_msg}")
            raise RuntimeError(f"Failed to add BGM: {error_msg}")
    
    def _add_bgm_to_video(
        self,
        video: str,
        bgm_path: str,
        output: str,
        volume: float = 0.2,
        mode: Literal["once", "loop"] = "loop"
    ) -> str:
        """
        内部辅助函数：处理含有系统默认或用户自定义预设字符串名称的 BGM 文件注入工作。
        """
        # 解析真实的文件路径地址并引发抛出未找到处理
        resolved_bgm = self._resolve_bgm_path(bgm_path)
        
        loop = (mode == "loop")
        return self.add_bgm(
            video=video,
            bgm=resolved_bgm,
            output=output,
            bgm_volume=volume,
            loop=loop,
            fade_in=0.0
        )
    
    def _get_unique_temp_path(self, prefix: str, original_filename: str) -> str:
        """
        生成附有 UUID Hash 特征的安全防并发混写的临时暂存交换路径地址。
        """
        from pixelle_video.utils.os_util import get_temp_path
        
        unique_id = uuid.uuid4().hex[:8]
        return get_temp_path(f"{prefix}_{unique_id}_{original_filename}")
    
    def _resolve_bgm_path(self, bgm_path: str) -> str:
        """
        带自动级联查找功能的 BGM 路径查询探测与解析策略树。
        优先级为:
        1. 提供了具体的物理存储绝对或相对路径
        2. 自定义上传数据卷区中的 "data/bgm/" 资源
        3. 代码库绑定的出厂内置 "bgm/" 库
        """
        if os.path.exists(bgm_path):
            return os.path.abspath(bgm_path)
        
        if resource_exists("bgm", bgm_path):
            return get_resource_path("bgm", bgm_path)
        
        tried_paths = [
            os.path.abspath(bgm_path),
            f"data/bgm/{bgm_path} or bgm/{bgm_path}"
        ]
        
        available_bgm = self._list_available_bgm()
        available_msg = f"\n  Available BGM files: {', '.join(available_bgm)}" if available_bgm else ""
        
        raise FileNotFoundError(
            f"BGM file not found: '{bgm_path}'\n"
            f"  Tried paths:\n"
            f"    1. {tried_paths[0]}\n"
            f"    2. {tried_paths[1]}"
            f"{available_msg}"
        )
    
    def _list_available_bgm(self) -> list[str]:
        """查询检索所有存在的音乐素材资源作为帮助字典菜单输出"""
        try:
            all_files = list_resource_files("bgm")
            audio_extensions = ('.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac')
            return sorted([f for f in all_files if f.lower().endswith(audio_extensions)])
        except Exception as e:
            logger.warning(f"Failed to list BGM files: {e}")
            return []
    
    def _trim_video_to_duration(self, video: str, target_duration: float) -> str:
        """执行长尾切割修剪功能的内部安全操作包，它直接在原画上抽减尾帧不影响整体感官。"""
        output = self._get_unique_temp_path("trimmed", os.path.basename(video))
        
        try:
            # Use stream copy when possible for fast trimming / 不重编解包画质以闪电般速度复制修剪头文件时间轴标记位
            input_stream = ffmpeg.input(video, t=target_duration)
            output_kwargs = {"vcodec": "copy"}
            if self.has_audio_stream(video):
                output_kwargs["acodec"] = "copy"
            (
                input_stream
                .output(output, **output_kwargs)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True, quiet=True)
            )
            return output
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg error trimming video: {error_msg}")
            raise RuntimeError(f"Failed to trim video: {error_msg}")
    
    def _pad_video_to_duration(self, video: str, target_duration: float, pad_strategy: str = "freeze") -> str:
        """
        在结尾无动作地定格冷冻画面帧直至满足指定的垫补时长的后处理补偿模块（为了解决 AI 生视频时长不如文本声音长的情况）。
        """
        output = self._get_unique_temp_path("padded", os.path.basename(video))
        
        video_duration = self._get_video_duration(video)
        pad_duration = target_duration - video_duration
        
        if pad_duration <= 0:
            return video
        
        try:
            input_video = ffmpeg.input(video)
            video_stream = input_video.video
            
            if pad_strategy == "freeze":
                # 利用基于 tpad 扩展定格帧功能补丁来拷贝末画面并一直静止显示
                video_stream = video_stream.filter('tpad', stop_mode='clone', stop_duration=pad_duration)
                
                (
                    ffmpeg
                    .output(
                        video_stream,
                        output,
                        vcodec='libx264',
                        preset='fast',
                        crf=23
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
            else:  # black屏方案
                probe = ffmpeg.probe(video)
                video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                width = int(video_info['width'])
                height = int(video_info['height'])
                fps_str = video_info['r_frame_rate']
                fps_num, fps_den = map(int, fps_str.split('/'))
                fps = fps_num / fps_den if fps_den != 0 else 30
                
                black_input = ffmpeg.input(
                    f'color=c=black:s={width}x{height}:r={fps}',
                    f='lavfi',
                    t=pad_duration
                )
                
                video_stream = ffmpeg.concat(video_stream, black_input.video, v=1, a=0)
                
                (
                    ffmpeg
                    .output(
                        video_stream,
                        output,
                        vcodec='libx264',
                        preset='fast',
                        crf=23
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True, quiet=True)
                )
            
            return output
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg error padding video: {error_msg}")
            raise RuntimeError(f"Failed to pad video: {error_msg}")

