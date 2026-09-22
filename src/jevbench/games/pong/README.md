# Pong environment

The benchmark policy controls the right paddle against a deterministic tracking bot. Difficulty changes the bot's paddle speed, reaction interval, and seeded aiming error. The match ends when either side reaches three points or simulated time reaches 120 seconds.

The primary score is points scored. Match success requires more points than the opponent. The result also reports point differential, paddle returns, rallies, and simulated time.

Lockstep mode advances 100 ms after every decision and ignores measured latency. In real-time mode, physics runs under the previous paddle command until the answer arrives. An answer inside the 100 ms control interval takes effect for the rest of that interval; a slower answer leaves the old command active through every interval it misses. Results report the number of late decisions alongside latency and simulated time.
