export async function requestOrDefault(requestPromise, fallbackValue, label = 'request') {
  try {
    const response = await requestPromise;
    return response?.data ?? fallbackValue;
  } catch (error) {
    console.warn(`Non-blocking load failure for ${label}:`, error);
    return fallbackValue;
  }
}
