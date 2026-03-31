use anyhow::Result;
use ndarray::{Array2, ArrayView1, ArrayView2};

pub struct WMatrix {
    data: Array2<f32>, // shape [embed_dim, 32]
}

impl WMatrix {
    /// Load W from a binary file (npy-like: first 8 bytes = rows,cols as u32 LE, then f32 data).
    pub fn load(path: &str) -> Result<Self> {
        let raw = std::fs::read(path)?;
        if raw.len() < 8 {
            anyhow::bail!("W file too short");
        }
        let rows = u32::from_le_bytes(raw[0..4].try_into()?) as usize;
        let cols = u32::from_le_bytes(raw[4..8].try_into()?) as usize;
        let expected = 8 + rows * cols * 4;
        if raw.len() < expected {
            anyhow::bail!("W file truncated: need {} bytes, got {}", expected, raw.len());
        }
        let floats: Vec<f32> = raw[8..]
            .chunks_exact(4)
            .take(rows * cols)
            .map(|b| f32::from_le_bytes(b.try_into().unwrap()))
            .collect();
        let data = Array2::from_shape_vec((rows, cols), floats)?;
        Ok(Self { data })
    }

    /// Identity-like init: W[i, i % 32] = 1.0, rest = 0.0, plus small noise.
    pub fn identity_init(embed_dim: usize) -> Self {
        let mut data = Array2::<f32>::zeros((embed_dim, 32));
        for i in 0..embed_dim {
            data[[i, i % 32]] = 1.0;
        }
        for i in 0..embed_dim {
            for j in 0..32 {
                let noise = ((i * 37 + j * 13) % 100) as f32 * 0.0001;
                data[[i, j]] += noise;
            }
        }
        Self { data }
    }

    /// Single embedding → [32] via SIMD-accelerated dot product (matrixmultiply).
    /// Replaces the naive nested loop — ndarray uses SIMD internally via matrixmultiply.
    pub fn project(&self, embedding: &[f32]) -> [f32; 32] {
        let emb = ArrayView1::from(embedding);
        // emb[embed_dim] · W[embed_dim, 32] → out[32]
        let out_nd = emb.dot(&self.data);
        let mut out = [0f32; 32];
        for (i, &v) in out_nd.iter().enumerate() {
            out[i] = sigmoid(v);
        }
        out
    }

    /// Batch GEMM: N embeddings → N × [32] in a single matrix multiply.
    /// batch[N, embed_dim] · W[embed_dim, 32] → result[N, 32]
    /// Dramatically faster than calling project() N times individually.
    pub fn project_batch(&self, embeddings: &[Vec<f32>]) -> Vec<[f32; 32]> {
        if embeddings.is_empty() {
            return vec![];
        }
        let n = embeddings.len();
        let dim = self.data.nrows();

        // Stack into contiguous 2D array [N, embed_dim]
        let flat: Vec<f32> = embeddings.iter().flat_map(|e| e.iter().copied()).collect();
        let batch = ArrayView2::from_shape((n, dim), &flat)
            .expect("embedding dimensions must match W rows");

        // Single GEMM: [N, embed_dim] × [embed_dim, 32] = [N, 32]
        let result = batch.dot(&self.data);

        result
            .outer_iter()
            .map(|row| {
                let mut out = [0f32; 32];
                for (i, &v) in row.iter().enumerate() {
                    out[i] = sigmoid(v);
                }
                out
            })
            .collect()
    }

    /// Save W to binary file (same format as load).
    pub fn save(&self, path: &str) -> Result<()> {
        let (rows, cols) = self.data.dim();
        let mut buf = Vec::with_capacity(8 + rows * cols * 4);
        buf.extend_from_slice(&(rows as u32).to_le_bytes());
        buf.extend_from_slice(&(cols as u32).to_le_bytes());
        for &v in self.data.iter() {
            buf.extend_from_slice(&v.to_le_bytes());
        }
        std::fs::write(path, buf)?;
        Ok(())
    }
}

#[inline(always)]
fn sigmoid(x: f32) -> f32 {
    1.0 / (1.0 + (-x).exp())
}
