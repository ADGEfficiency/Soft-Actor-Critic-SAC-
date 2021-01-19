import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from utils import minimum_target


def make_qfunc(obs_shape, n_actions, name, size_scale=1):

    in_obs = keras.Input(shape=obs_shape)
    in_act = keras.Input(shape=n_actions)
    inputs = tf.concat([in_obs, in_act], axis=1)

    net = layers.Dense(64*size_scale, activation='relu')(inputs)
    net = layers.Dense(32*size_scale, activation='relu')(inputs)
    q_value = layers.Dense(1, activation='linear')(net)

    return keras.Model(
        inputs=[in_obs, in_act],
        outputs=q_value,
        name=name
    )


def update_target_network(online, target, rho, step=None, writer=None):
    for o, t in zip(online.trainable_variables, target.trainable_variables):
        t.assign(rho * t.value() + (1 - rho) * o.value())

    if writer:
        with writer.as_default():
            tf.summary.histogram(f'{target.name} target weights', target.trainable_variables[-2], step=step)


def initialize_qfuncs(env, size_scale=1):
    obs_shape = env.observation_space.shape
    n_actions = env.action_space.shape

    q1 = make_qfunc(obs_shape, n_actions, 'q1', size_scale)
    q1_target = make_qfunc(obs_shape, n_actions, 'q1-target', size_scale)
    q2 = make_qfunc(obs_shape, n_actions, 'q2', size_scale)
    q2_target = make_qfunc(obs_shape, n_actions, 'q2-target', size_scale)

    update_target_network(online=q1, target=q1_target, rho=0.0)
    update_target_network(online=q2, target=q2_target, rho=0.0)
    onlines = [q1, q2]
    targets = [q1_target, q2_target]
    return onlines, targets


def update_qfuncs(
    batch,
    actor,
    onlines,
    targets,
    log_alpha,
    writer,
    optimizers,
    counters,
    hyp
):
    next_state_act, log_prob, _ = actor(batch['next_observation'])
    next_state_target = minimum_target(batch['next_observation'], next_state_act, targets)

    al = tf.exp(log_alpha)
    ga = hyp['gamma']
    target = batch['reward'] + ga * (1 - batch['done']) * (next_state_target - al * log_prob)

    step = counters['qfunc_updates']
    with writer.as_default():
        tf.summary.scalar('qfunc target', tf.reduce_mean(target), step=step)

        for onl, optimizer in zip(onlines, optimizers):
            with tf.GradientTape() as tape:
                q_value = onl([batch['observation'], batch['action']])
                loss = tf.keras.losses.MSE(q_value, target)

            grads = tape.gradient(loss, onl.trainable_variables)
            grads, _ = tf.clip_by_global_norm(grads, 5.0)
            optimizer.apply_gradients(zip(grads, onl.trainable_variables))
            tf.summary.scalar(f'online {onl.name} loss', tf.reduce_mean(loss), step=step)
            tf.summary.scalar(f'online {onl.name} q_value', tf.reduce_mean(q_value), step=step)

        counters['qfunc_updates'] += 1
