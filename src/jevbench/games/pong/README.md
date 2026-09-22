# Pong environment

The benchmark policy controls the right paddle against a deterministic tracking bot. Difficulty changes the bot's paddle speed, reaction interval, and seeded aiming error. The match ends when either side reaches three points or simulated time reaches 120 seconds.

The primary score is points scored. Match success requires more points than the opponent. The result also reports point differential, paddle returns, rallies, and simulated time.

Lockstep mode advances 100 ms after every decision. Real-time mode advances by the measured model latency, with a 100 ms minimum. The match time limit is the only upper bound. The previous paddle command stays active while the model answers.
