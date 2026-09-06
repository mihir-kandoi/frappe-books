import { Doc } from 'fyo/model/doc';

/**
 * # Transactional
 *
 * Models that post ledger entries on submit extend `Transactional`. The
 * server creates, reverses and deletes the entries; the interface only uses
 * the marker to offer ledger links after submit.
 */

export abstract class Transactional extends Doc {
  date?: Date;

  get isTransactional() {
    return true;
  }
}
