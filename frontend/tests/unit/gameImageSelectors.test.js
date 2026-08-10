import assert from 'node:assert/strict'
import { test } from 'node:test'

import { sortDisplayImages } from '../../src/pages/browse-games/gameImageSelectors.js'

test('sortDisplayImages uses public image response fields only', () => {
  const images = [
    {
      id: 'image-c',
      image_url: '/c.jpg',
      is_primary: false,
      sort_order: 1,
    },
    {
      id: 'image-b',
      image_url: '/b.jpg',
      is_primary: false,
      sort_order: 0,
    },
    {
      id: 'image-a',
      image_url: '/a.jpg',
      is_primary: true,
      sort_order: 2,
    },
  ]

  assert.deepEqual(
    sortDisplayImages(images).map((image) => image.id),
    ['image-a', 'image-b', 'image-c'],
  )
  assert.deepEqual(
    images.map((image) => image.id),
    ['image-c', 'image-b', 'image-a'],
  )
})
