export function getMapCenter(points) {
  if (!Array.isArray(points) || points.length === 0) {
    return [10.8231, 106.6297];
  }

  const sum = points.reduce(
    (acc, point) => {
      acc.lat += point.latitude;
      acc.lng += point.longitude;
      return acc;
    },
    { lat: 0, lng: 0 }
  );

  return [sum.lat / points.length, sum.lng / points.length];
}
