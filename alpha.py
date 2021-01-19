import numpy as np
import tensorflow as tf


def initialize_log_alpha(
    env,
    initial_value
):
    target_entropy = - np.product(env.action_space.shape)

    log_alpha = tf.Variable(
        initial_value,
        trainable=True,
        name='log-alpha',
        dtype='float32'
    )
    return target_entropy, log_alpha


def update_alpha(
    batch,
    actor,
    log_alpha,
    target_entropy,
    optimizer,
    counters,
    writer
):
    obs = batch['observation']
    _, log_prob, _ = actor(obs)

    with tf.GradientTape() as tape:
        loss = -1.0 * tf.reduce_mean((tf.exp(log_alpha) * (log_prob + target_entropy)))

    grad = tape.gradient(loss, log_alpha)
    optimizer.apply_gradients(zip([grad, ], [log_alpha, ]))

    with writer.as_default():
        step = counters['alpha-updates']
        tf.summary.scalar('alpha-loss', tf.reduce_mean(loss), step=step)
        tf.summary.scalar('alpha', tf.exp(log_alpha), step=step)
        tf.summary.scalar('log-alpha', log_alpha, step=step)
        tf.summary.scalar('alpha-log-probs', tf.reduce_mean(log_prob), step=step)
        counters['alpha-updates'] += 1
